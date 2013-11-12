"""Copyright 2013 Jay Booth

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import whisper
import importlib
import os
from os.path import join, dirname, exists, sep
from abc import ABCMeta,abstractmethod
from carbon.conf import settings
from carbon import log

# class DB is a generic DB layer to support graphite.  Plugins can provide an implementation satisfying the following functions
# by configuring DB_MODULE, DB_INIT_FUNC and DB_INIT_ARG

# the global variable APP_DB will be initialized as the return value of DB_MODULE.DB_INIT_FUNC(DB_INIT_ARG)
# we will throw an error if the provided value does not implement our abstract class DB below


class DB:
    __metaclass__= ABCMeta

    # returns info for the underlying db (including 'aggregationMethod')
    @abstractmethod
    def info(self, metric):
        pass

    @abstractmethod
    def setAggregationMethod(self, metric, value):
        pass

    @abstractmethod
    def create(self, metric, archiveConfig, xFilesFactor, aggregationMethod, isSparse, doFallocate):
        pass

    @abstractmethod
    def update_many(self, metric, datapoints):
        pass

    @abstractmethod
    def exists(self,metric):
        pass

    @abstractmethod
    def fetch(self,metric,startTime,endTime):
        pass

def getFilesystemPath(metric):
  metric_path = metric.replace('.',sep).lstrip(sep) + '.wsp'
  return join(settings.LOCAL_DATA_DIR, metric_path)

class WhisperDB:
    def info(self,metric):
        return whisper.info(getFilesystemPath(metric))

    def setAggregationMethod(self,metric,value):
        return whisper.setAggregationMethod(getFilesystemPath(metric),value)

    def create(self,metric,archiveConfig,xFilesFactor,aggregationMethod,sparseCreate,fallocateCreate):
        dbFilePath = getFilesystemPath(metric)
        dbDir = dirname(dbFilePath)
        try:
            os.makedirs(dbDir, 0755)
        except OSError as e:
            log.err("%s" % e)
        log.creates("creating database file %s (archive=%s xff=%s agg=%s)" %
                    (dbFilePath, archiveConfig, xFilesFactor, aggregationMethod))
        return whisper.create(dbFilePath, archiveConfig,xFilesFactor,aggregationMethod,sparseCreate,fallocateCreate)

    def update_many(self,metric,datapoints):
        return whisper.update_many(getFilesystemPath(metric), datapoints)

    def exists(self,metric):
        return exists(getFilesystemPath(metric))

    def fetch(self,metric,startTime,endTime):
        return whisper.fetch(getFilesystemPath(metric),startTime,endTime)

# application database
APP_DB = WhisperDB() # default implementation

# if we've configured a module to override, put that one in place instead of the default whisper db
if (settings.DB_MODULE != "whisper" and settings.DB_INIT_FUNC != ""):
    m = importlib.import_module(settings.DB_MODULE)
    dbInitFunc = getattr(m,settings.DB_INIT_FUNC)
    APP_DB = dbInitFunc(settings.DB_INIT_ARG)
    assert isinstance(APP_DB,DB)