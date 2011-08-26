#!/usr/bin/python

import sys, vobject

from PyKDE4.akonadi import *
from PyKDE4.kdeui import *
from PyKDE4.kdecore import *
from PyKDE4.kio import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class Settings( KConfigSkeleton ):
	""" Settings object to bypass kconfig_compiler limitation

	See: http://www.dennogumi.org/2009/10/howto-kconfigxt-with-pykde4 """

	def __init__( self, name="akonadi_pygcal_resource", group="General" ):
		""" Constructor """

		KConfigSkeleton.__init__( self, name )

		self.setCurrentGroup( group )

		self._path_data = QString()
		self._path = self.addItemPath("Path", self._path_data)

		self._readonly_data = bool()
		self._readonly = self.addItemBool("ReadOnly", self._readonly_data, False)

		self.readConfig()

	@property
	def path(self):
		""" Return the path property of the vcard dir setting. """
		return self._path.value()

	@property
	def readonly(self):
		""" Return if the vcard dir is in ReadOnly or not. """
		return self._readonly.value()


class PyVCardDirResource( Akonadi.ResourceBase ):
	""" Python object that rapresent the Akonadi Resource. """

	def __init__( self, id ):
		""" Constructor

		TODO: you can put any resource specific initialization code here.
		"""
		Akonadi.ResourceBase.__init__( self, id )
		self.id = id
		self.settings = Settings( self.id )
	
	def configure( self, windowId ):
		"""
		TODO: this method is usually called when a new resource is being
		added to the Akonadi setup. You can do any kind of user interaction here,
		e.g. showing dialogs.
		The given window ID is usually useful to get the correct
		"on top of parent" behavior if the running window manager applies any kind
		of focus stealing prevention technique
		
		If the configuration dialog has been accepted by the user by clicking Ok,
		the signal configurationDialogAccepted() has to be emitted, otherwise, if
		the user canceled the dialog, configurationDialogRejected() has to be emitted.
		"""

		oldPath = self.settings.path
		if oldPath.isEmpty():
			url = KUrl(QDir.homePath())
		else:
			url = KUrl(oldPath)

		title = i18nc( "@title:window", "Select vCard folder" )
		newPath = KFileDialog.getExistingDirectory( url, QWidget(), title )

		if newPath.isEmpty():
			self.configurationDialogRejected()
			return 

		if oldPath == newPath:
			self.configurationDialogRejected()
			return

		self.settings._path.setValue(newPath)

		self.settings.writeConfig()
		self.configurationDialogAccepted()

		self.synchronize()
		self.changeRecorder().itemFetchScope().fetchFullPayload()

	def retrieveCollections(self):
		"""
		TODO: this method is called when Akonadi wants to have all the
		collections your resource provides.
		Be sure to set the remote ID and the content MIME types
		"""
		c = Akonadi.Collection()
		c.setParent(Akonadi.Collection.root())
		c.setRemoteId( self.settings.path );
		c.setName( self.name() );

		mimeType = QStringList(QLatin1String("text/directory"))
		c.setContentMimeTypes(mimeType)

		collections = [c]
		self.collectionsRetrieved(collections)

	def retrieveItems(self, collection):
		"""
		TODO: this method is called when Akonadi wants to know about all the
		items in the given collection. You can but don't have to provide all the
		data for each item, remote ID and MIME type are enough at this stage.
		Depending on how your resource accesses the data, there are several
		different ways to tell Akonadi when you are done.
		"""
		path = collection.remoteId()
		dir = QDir(path)

		#filters = QStringList("*.vcf")
		#fileList = dir.entryList( filters, QDir.Files )
		fileList = dir.entryList( QDir.Files )

		items = []
		for file in fileList:
			item = Akonadi.Item(QLatin1String( "text/directory" ))
			item.setRemoteId(path + QLatin1Char('/').toLatin1() + file)
			item.setParentCollection(collection)
			items.append(item)

		self.itemsRetrieved( items )

	def retrieveItem(self, item, parts):
		"""
		TODO: this method is called when Akonadi wants more data for a given item.
		You can only provide the parts that have been requested but you are allowed
		to provide all in one go
		"""
		fileName = item.remoteId()

		file = QFile(fileName)
		if not file.open(QIODevice.ReadOnly):
			return False

		data = file.readAll()
		if not file.error() == QFile.NoError :
			return False

		card = vobject.readOne(data.data())

		if not card.n.value or not card.fn.value or not card.email.value:
			return False

		newItem = Akonadi.Item(item)
		newItem.setPayloadFromData(data)

		self.itemRetrieved(newItem)
		return True

	def aboutToQuit(self):
		"""
		TODO: any cleanup you need to do while there is still an active
		event loop. The resource will terminate after this method returns
		"""
		pass


	def itemAdded(self, item, collection):
		"""
		TODO: this method is called when somebody else, e.g. a client application,
		has created an item in a collection managed by your resource.

		NOTE: There is an equivalent method for collections, but it isn't part
		of this template code to keep it simple
		"""
		path = collection.remoteId()

		if item.hasPayload():
			addressee = item.payloadData()

		if addressee.uid().isEmpty():
			addressee.setUid(KRandom.randomString(10))

		#file = QFile( path + QLatin1Char( '/' ) + addressee.uid() + QLatin1String( ".vcf" ) )
		file = QFile( path + QLatin1Char( '/' ) + addressee.uid() )

		if not file.open(QIODevice.WriteOnly):
			return

		card = vobject.readOne(addressee.data())
		file.write( card.prettyPrint())
		if not file.error() == QFile.NoError :
			return
 
		newItem = Akonadi.Item(item)
		newItem.setRemoteId(file.fileName())
		newItem.setPayloadFromData(addressee)

		self.changeCommitted(newItem)


	def itemChanged(self, item, parts):
		"""
		TODO: this method is called when somebody else, e.g. a client application,
		has changed an item managed by your resource.
		
		NOTE: There is an equivalent method for collections, but it isn't part
		of this template code to keep it simple
		"""
		fileName = item.remoteId()

		if item.hasPayload() :
			addressee = item.payloadData()

		if addressee.uid().isEmpty():
			addressee.setUid(KRandom.randomString(10))

		file = QFile(fileName)

		if not file.open(QIODevice.WriteOnly):
			return

		card = vobject.readOne(addressee.data())
		file.write( card.prettyPrint())
		if not file.error() == QFile.NoError :
			return
 
		newItem = Akonadi.Item(item)
		newItem.setPayloadFromData(addressee)

		self.changeCommitted(newItem)


	def itemRemoved(self, item):
		"""
		TODO: this method is called when somebody else, e.g. a client application,
		has deleted an item managed by your resource.
		
		NOTE: There is an equivalent method for collections, but it isn't part
		of this template code to keep it simple
		"""
		fileName = item.remoteId()

		QFile.remove(fileName)

		self.changeCommitted(newItem)
	 

def main():
	app_name = "akonadi_pygcal_resource.py"
	program_name = ki18n("Python Akonadi Resource for Google Calendar")
	about_data = KAboutData(QByteArray(app_name), "", program_name, QByteArray("0.1"))
	options = KCmdLineOptions()
	options.add(QByteArray("identifier <argument>"), ki18n("The identifier for akonadi resource"))
	KCmdLineArgs.init(sys.argv, about_data)
	KCmdLineArgs.addCmdLineOptions(options)
	app = KApplication()

	arg = KCmdLineArgs.parsedArgs()
	if( arg.isSet("identifier")):
		identifier = arg.getOption("identifier")
		p = PyVCardDirResource( identifier )
		qDebug( " Option --identifier = %s" %(identifier) )
		app.exec_()
	else:
		error = ki18n( "No identifier provide using --identifier option" ).toString()
		KCmdLineArgs.usageError( error )
	
if __name__ == "__main__":
	main()
