#!/usr/bin/python

import sys, vobject

from PyKDE4.akonadi import *
from PyKDE4.kdeui import *
from PyKDE4.kdecore import *
from PyKDE4.kio import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class Settings( KConfigSkeleton ):

	def __init__( self, name="akonadi_pygcal_resource", group="General" ):

		KConfigSkeleton.__init__( self, name )

		self.setCurrentGroup( group )

		self._path_data = QString()
		self._path = self.addItemPath("Path", self._path_data)

		self._readonly_data = bool()
		self._readonly = self.addItemBool("ReadOnly", self._readonly_data, False)

		self.readConfig()

	@property
	def path(self):
		return self._path.value()

	@property
	def readonly(self):
		return self._readonly.value()


class PyVCardDirResource( Akonadi.ResourceBase ):

	def __init__( self, id ):
		Akonadi.ResourceBase.__init__( self, id )
		self.id = id
		self.settings = Settings( self.id )
	
	def configure( self, windowId ):

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
		c = Akonadi.Collection()
		c.setParent(Akonadi.Collection.root())
		c.setRemoteId( self.settings.path );
		c.setName( self.name() );

		mimeType = QStringList(QLatin1String("text/directory"))
		c.setContentMimeTypes(mimeType)

		collections = [c]
		self.collectionsRetrieved(collections)

	def retriveItems(self, collection):
		path = collection.remoteId()
		dir = QDir(path)

		#filters = QStringList("*.vcf")
		#fileList = dir.entryList( filters, QDir.Files )
		fileList = dir.entryList( QDir.Files )

		items = []
		for file in fileList:
			item = Akonadi.Item(QLatin1String( "text/directory" ))
			item.setRemoteId(path + QLatin1Char('/') + file)

			items.append(item)

		self.itemsRetrieved( items )

	def retriveItem(self, item):
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

	def itemAdded(self, item, collection):
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


	def itemChanged(self, item):
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
