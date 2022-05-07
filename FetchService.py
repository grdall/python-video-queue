import os
import sys
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from grdException.ArgumentException import ArgumentException
from grdUtil.BashColor import BashColor
from grdUtil.FileUtil import mkdir
from grdUtil.InputUtil import sanitize
from grdUtil.PrintUtil import printS
from pytube import Channel

from enums.StreamSourceType import StreamSourceType
from model.QueueStream import QueueStream
from model.StreamSource import StreamSource
from PlaylistService import PlaylistService
from QueueStreamService import QueueStreamService
from StreamSourceService import StreamSourceService

load_dotenv()
DEBUG = eval(os.environ.get("DEBUG"))
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH")

class FetchService():
    playlistService: PlaylistService = None
    queueStreamService: QueueStreamService = None
    streamSourceService: StreamSourceService = None

    def __init__(self):
        self.playlistService: PlaylistService = PlaylistService()
        self.queueStreamService: QueueStreamService = QueueStreamService()
        self.streamSourceService: StreamSourceService = StreamSourceService()

        mkdir(LOCAL_STORAGE_PATH)

    def fetch(self, playlistId: str, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> int:
        """
        Fetch new videos from watched sources, adding them in chronological order.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            int: number of videos added
        """
        
        if(batchSize < 1):
            raise ArgumentException("fetch - batchSize was less than 1.")

        playlist = self.playlistService.get(playlistId)
        if(playlist == None):
            return 0

        newStreams = []
        for sourceId in playlist.streamSourceIds:
            source = self.streamSourceService.get(sourceId)
            
            if(source == None):
                printS("StreamSource with ID ", sourceId, " could not be found. Consider removing it using the purge commands.", color = BashColor.FAIL)
                continue
            
            if(not source.enableFetch):
                continue

            fetchedStreams = []
            _takeAfter = takeAfter if(not takeNewOnly) else source.lastSuccessfulFetched
            
            if(source.isWeb):
                if(source.streamSourceTypeId == StreamSourceType.YOUTUBE.value):
                    fetchedStreams = self.fetchYoutube(source, batchSize, _takeAfter, takeBefore, takeNewOnly)
                else:
                    # TODO handle other sources
                    continue
            else:
                fetchedStreams = self.fetchDirectory(source, batchSize, _takeAfter, takeBefore, takeNewOnly)

            if(len(fetchedStreams) > 0):
                source.lastSuccessfulFetched = datetime.now()
            
            source.lastFetchedIds = fetchedStreams[1]
            source.lastFetched = datetime.now()
            updateSuccess = self.streamSourceService.update(source)
            if(updateSuccess):
                newStreams += fetchedStreams[0]
            else:
                printS("Could not update StreamSource \"", source.name, "\" (ID: ", source.id, "), streams could not be added: \n", fetchedStreams, color = BashColor.WARNING)
                
            sys.stdout.flush()

        updateResult = self.playlistService.addStreams(playlist.id, newStreams)
        if(len(updateResult) > 0):
            return len(newStreams)
        else:
            return 0

    def fetchYoutube(self, streamSource: StreamSource, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> tuple[List[QueueStream], List[str]]:
        """
        Fetch videos from YouTube.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            tuple[List[QueueStream], List[str]]: A tuple of List of QueueStream, and List of last YouTube IDs fetched
        """
        
        if(streamSource == None):
            raise ArgumentException("fetchYoutube - streamSource was None.")

        emptyReturn = ([], streamSource.lastFetchedIds)
        channel = Channel(streamSource.uri)

        if(channel == None or channel.channel_name == None):
            printS("Channel \"", streamSource.name, "\" (URL: ", streamSource.uri, ") could not be found or is not valid. Please remove it and add it back.", color = BashColor.FAIL)
            return emptyReturn

        printS("Fetching videos from ", channel.channel_name, "...")
        sys.stdout.flush()
        if(len(channel.video_urls) < 1):
            printS("Channel \"", channel.channel_name, "\" has no videos.", color = BashColor.WARNING)
            return emptyReturn

        newStreams = []
        streams = list(channel.videos)
        lastStreamId = streams[0].video_id
        if(takeNewOnly and takeAfter == None and lastStreamId in streamSource.lastFetchedIds):
            printS("DEBUG: fetchYoutube - last video fetched: \"", sanitize(streams[0].title), "\", YouTube ID \"", lastStreamId, "\"", color = BashColor.WARNING)
            printS("DEBUG: fetchYoutube - return due to takeNewOnly and takeAfter == None and lastStreamId in streamSource.lastFetchedIds", color = BashColor.WARNING)
            return emptyReturn
            
        for i, stream in enumerate(streams):
            if(takeNewOnly and stream.video_id in streamSource.lastFetchedIds):
                printS("DEBUG: fetchYoutube - name \"", sanitize(stream.title), "\", YouTube ID \"", stream.video_id, "\"", color = BashColor.WARNING)
                printS("DEBUG: fetchYoutube - break due to takeNewOnly and stream.video_id in streamSource.lastFetchedIds", color = BashColor.WARNING)
                break
            elif(not takeNewOnly and takeAfter != None and stream.publish_date < takeAfter):
                printS("DEBUG: fetchYoutube - break due to not takeNewOnly and takeAfter != None and stream.publish_date < takeAfter", color = BashColor.WARNING)
                break
            elif(not takeNewOnly and takeBefore != None and stream.publish_date > takeBefore):
                printS("DEBUG: fetchYoutube - continue due to not takeNewOnly and takeBefore != None and stream.publish_date > takeBefore", color = BashColor.WARNING)
                continue
            elif(i > batchSize):
                printS("DEBUG: fetchYoutube - break due to i > batchSize", color = BashColor.WARNING)
                break
            
            sanitizedTitle = sanitize(stream.title)
            printS("\tAdding \"", sanitizedTitle, "\"...")
            stream = QueueStream(name = sanitizedTitle, 
                uri = stream.watch_url, 
                isWeb = True,
                streamSourceId = streamSource.id,
                watched = None,
                backgroundContent = streamSource.backgroundContent,
                added = datetime.now())
            newStreams.append(stream)
            
        if(len(newStreams) == 0):
            # printS("No new videos detected.", color = BashColor.OKGREEN)
            return emptyReturn
            
        streamSource.lastFetchedIds.append(lastStreamId)
        if(len(streamSource.lastFetchedIds) > batchSize):
            streamSource.lastFetchedIds.pop(0)
        
        return (newStreams, streamSource.lastFetchedIds)

    def fetchDirectory(self, streamSource: StreamSource, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> tuple[List[QueueStream], str]:
        """
        Fetch streams from a local directory.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            tuple[List[QueueStream], str]: A tuple of List of QueueStream, and the last filename fetched 
        """
        
        if(streamSource == None):
            raise ValueError("fetchDirectory - streamSource was None")

        emptyReturn = ([], streamSource.lastFetchedIds)
        return emptyReturn
    
    def resetPlaylistFetch(self, playlistIds: List[str]) -> int:
        """
        Reset the fetch-status for sources of a playlist and deletes all streams.

        Args:
            playlistIds (List[str]): list of playlistIds 
            
        Returns:
            int: number of playlists reset
        """
        
        result = 0
        for playlistId in playlistIds:            
            playlist = self.playlistService.get(playlistId)
            deleteUpdateResult = True
            
            for queueStreamId in playlist.streamIds:
                deleteStreamResult = self.queueStreamService.delete(queueStreamId)
                deleteUpdateResult = deleteUpdateResult and deleteStreamResult != None
            
            playlist.streamIds = []
            updateplaylistResult = self.playlistService.update(playlist)
            deleteUpdateResult = deleteUpdateResult and updateplaylistResult != None
            
            for streamSourceId in playlist.streamSourceIds:
                streamSource = self.streamSourceService.get(streamSourceId)
                streamSource.lastFetched = None
                updateStreamResult = self.streamSourceService.update(streamSource)
                deleteUpdateResult = deleteUpdateResult and updateStreamResult != None
            
            if(deleteUpdateResult):
                result += 1
                
        return result
