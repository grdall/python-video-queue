from datetime import datetime
import uuid

class StreamSource:
    def __init__(self, 
                 name: str = None, 
                 uri: str = None, 
                 isWeb: bool = None,
                 streamSourceTypeId: int = None, 
                 enableFetch: bool = None, 
                 lastFetched: datetime = None, 
                 lastSuccessfulFetched: datetime = None,
                 lastFetchedId: str = None, # Legacy
                 lastFetchedIds: list[str] = None,
                 backgroundContent: bool = False, 
                 deleted: datetime = None,
                 added: datetime = datetime.now(),
                 id: str = None):
        self.name: str = name
        self.uri: str = uri
        self.isWeb: bool = isWeb
        self.streamSourceTypeId: int = streamSourceTypeId
        self.enableFetch: bool = enableFetch
        self.lastFetched: datetime = lastFetched
        self.lastSuccessfulFetched: datetime = lastSuccessfulFetched
        self.lastFetchedIds: list[str] = lastFetchedIds
        self.backgroundContent: bool = backgroundContent
        self.deleted: datetime = deleted
        self.added: datetime = added
        self.id: str = id

    def summaryString(self):
        return "".join(map(str, ["Name: ", self.name, 
        ", ID: ", self.id, 
        ", URI: ", self.uri,
        ", Enable fetch: ", self.enableFetch,
        ", Last fetch: ", self.lastSuccessfulFetched]))

    def simpleString(self):
        return "".join(map(str, ["\"", self.name, "\"",
        ", fetch enabled" if(self.enableFetch) else "",
        ", is web" if(self.isWeb) else "",
        ", Last fetch: ", self.lastSuccessfulFetched]))

    def detailsString(self, includeUri: bool = True, includeId: bool = True, includeDatetime: bool = True, includeListCount: bool = True):
        _uriString = ", uri: " + self.uri if(includeUri) else ""
        _idString = ", id: " + self.id if(includeId) else ""
        _lastFetchedIdsString = ", lastFetchedIds: " + self.lastFetchedIds if(includeId) else ""
        _lastFetchedString = ", lastFetched: " + str(self.lastFetched) if(includeDatetime) else ""
        _lastSuccessfulFetchedString = ", lastSuccessfulFetched: " + str(self.lastSuccessfulFetched) if(includeDatetime) else ""
        _deletedString = ", deleted: " + str(self.deleted) if(includeDatetime) else ""
        _addedString = ", added: " + str(self.added) if(includeDatetime) else ""
        
        return "".join(map(str, ["name: ", self.name,
        _uriString,
        ", isWeb: ", self.isWeb,
        ", streamSourceTypeId: ", self.streamSourceTypeId,
        ", enableFetch: ", self.enableFetch,
        _lastFetchedString,
        _lastSuccessfulFetchedString,
        _lastFetchedIdsString,
        ", backgroundContent: ", self.backgroundContent, 
        _deletedString,
        _addedString,
        _idString]))