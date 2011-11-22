#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, random, string, array, logging, datetime, time

from google.appengine.api import taskqueue, memcache

import bolognium
import bolognium.ext.db as db
import bolognium.ext.config as config
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth

import bolognium.lib.ndb.tasklets as tasklets
import bolognium.lib.ndb.context as context
import bolognium.lib.ndb.model as model

TIME_PERIOD_CODES = {
  u'MINUTE': 1,
  u'HOUR': 2,
  u'DAY': 3,
  u'MONTH': 4,
  u'YEAR': 5
}
TIME_PERIOD_NAMES = TIME_PERIOD_CODES.keys()

def get_metric(name):
  return db.Key(u'Metric', name).get()

def create_metric(name, is_sum=False, periods=[], **kwargs):
  try:
    for period in periods:
      assert period in TIME_PERIOD_NAMES
    assert len(periods)
    assert isinstance(is_sum, bool)
    assert isinstance(name, basestring)
    assert name
    assert len(name) < 500
    metric = Metric(id=name, periods=periods, is_sum=is_sum)
    metric.put()
  except AssertionError, e:
    raise
    raise BadArgumentsError(u'Method \'create_metric\' was called with '
      u'invalid arguments. MSG: %s' % e)
  except db.datastore_errors.Error, e:
    raise StorageError(u'Method \'create_metric\' raised datastore error '
      u'on save. MSG: %s' % e)
  return metric
  
class Metric(db.Model):
  periods = db.NameProperty(repeated=True)
  is_sum = db.BooleanProperty(default=False)

  def _period_data_record_name(self, period, timestamp):
    if period in self.periods and period in TIME_PERIOD_NAMES:
      time_key = None
      if period == u'MINUTE':
        time_key = u'%d-%d-%d-%d-%d' % (timestamp.year, timestamp.month, 
          timestamp.day, timestamp.hour, timestamp.minute)
      elif period == u'HOUR':
        time_key = u'%d-%d-%d-%d-_' % (timestamp.year, timestamp.month, 
          timestamp.day, timestamp.hour)
      elif period == u'DAY':
        time_key = u'%d-%d-%d-_-_' % (timestamp.year, timestamp.month, 
          timestamp.day)
      elif period == u'MONTH':
        time_key = u'%d-%d-_-_-_' % (timestamp.year, timestamp.month)
      elif period == u'YEAR':
        time_key = u'%d-_-_-_-_' % timestamp.year
    if time_key:
      return u'%s-%s' % (self.key.id(), time_key)
    raise InvalidPeriodError(u'Invalid or disabled period supplied in '
      u'\'_period_data_record_name\' for Metric(\'%s\'). PERIOD: %s' % 
      (self.name, period))

  def _period_data_record_names(self, timestamp):
    keys = {}
    for period in TIME_PERIOD_NAMES:
      keys[period] = _period_data_record_name(period=period, 
        timestamp=timestamp)
    return keys

  def get_metric_data_rows_by_timestamp(self, timestamp):
    records = {}
    for period in TIME_PERIOD_NAMES:
      record_names[period] = _period_data_record_name(period=period, 
        timestamp=timestamp)
  
  @model.transactional
  def apply_delta(self, delta, timestamp=None):
    if timestamp is None:
      timestamp = datetime.datetime.now()
    for period in self.periods:
      insert_work_with_custom_retries(retries=5, name=\
        self._period_data_record_name(period, timestamp), delta=delta)

class SequenceMarker(db.Model):
  #_use_cache = False
  #_use_memcache = False

  i = db.IntegerProperty(default=0)

  #knuthed_sequence = db.IntegerProperty(default=0) #do I need this? I don't believe so.
  applied = db.BooleanProperty(default=False)
  delta = db.IntegerProperty(indexed=False)

  @classmethod
  def get_batch_index_lock(cls, name, retries=1): #should probably be set to more than 1.
    assert retries > 0
    for x in xrange(retries):
      _lock = cls._get_batch_index_lock(name)
      if _lock:
        return _lock
    raise Exception(u'Could not get batch index lock for name: %s' % name)

  @classmethod
  def _get_batch_index_lock(cls, name):
    utils.log.warn(u'Getting batch index for ##############: %s' % name)
    client, batch_index = cls.get_latest_batch_index(name)
    #if no batch_index, trigger a task to create a new one.
    if batch_index:
      utils.log.info(u'Got batch index for %s: %s' % (name, batch_index))
      batch_index_lock = cls.get_lock_on_batch_index(name, batch_index)
      if batch_index_lock:
        utils.log.info(u'Got lock on work key: %s-%s' % (name, batch_index))
        #success
        return batch_index_lock
      else:
        client.cas(u'/BATCH_INDEX/%s' % name, None)
    utils.log.info(u'batch_index##############: %s' % batch_index)

  @classmethod
  def get_latest_batch_index(cls, name):
    """
    This should give back the batch_index saved for 'name' in memcache, or
    if that key doesn't exist, fallback to trigger (possibly) the creation
    of the next batch index, and wait for it to appear in memcache, while 
    checking for 'working' signals from the task that is apparently handling 
    the job.
    """
    client, batch_index = cls.get_batch_index_from_memcache(name)
    if batch_index: #Should be lockable right now
      return client, batch_index
    #New index is on it's way. Sleep my child.
    cls.spawn_next_batch_index(name)
    for x in xrange(10):
      utils.log.info(u'zzz-%d' % x)
      time.sleep(.05)
      client, batch_index = cls.get_batch_index_from_memcache(name)
      if batch_index:
        return client, batch_index
    return client, None

  @classmethod
  def get_lock_on_batch_index(cls, name, batch_index):
    try:
      return WriteLock(u'%s-%d' % (name, batch_index))
    except Exception, e: 
      return None

    except Exception, e: 
      return None
  
  @classmethod
  def spawn_next_batch_index(cls, name):
    taskqueue.add(url=u'/task/metric-spawn-work-batch', #target='metric-worker',
    queue_name=u'metric-meta-workers', countdown=0, method=u'POST', params={u'name':name})

    #wait a set amount of time for the record to appear in memcache, and then return it.
    #raise SequenceError(u'Ran out of time waiting for next sequence index '
    #  u'to be spawned.')

  @classmethod
  def trigger_close_batch_work_task(cls, name):
    taskqueue.add(url=u'/task/metric-close-work-batch',  target='metric-worker',
    queue_name=u'metric-meta-workers', countdown=2, method=u'POST', 
    params={u'name':name})
    
  @classmethod
  def get_batch_index_from_memcache(cls, name, client=None):
    # Get latest batch sequence position
    client = client if isinstance(client, memcache.Client) else memcache.Client()
    res = client.get(u'/BATCH_INDEX/%s' % name)
    return client, res if isinstance(res, int) else None

  @classmethod
  def add_batch_index_to_memcache(cls, name, value):
    assert isinstance(value, int)
    return memcache.add(u'/BATCH_INDEX/%s' % name, value)

  @classmethod
  def update_batch_index_in_memcache(cls, name, change_to, change_from=None):
    client, batch_index = cls.get_batch_index_from_memcache(name)
    try:
      assert change_from == batch_index
      return client.cas(u'/BATCH_INDEX/%s' % name, change_to)
    except AssertionError, e:
      pass

  @classmethod
  def get_batch_index_working_signal(cls, name):
    return memcache.get(str(name))

class MetricData(db.Model):
  #_use_cache = False
  _use_memcache = False

  delta = db.IntegerProperty(default=0)
  last_applied = db.IntegerProperty(default=0)
  last_created = db.IntegerProperty(default=0)

  @classmethod
  def trigger_batch_work_task(cls, work_key):
    try:
      taskqueue.add(url=u'/task/metric-apply-work-batch', target='metric-worker',
        queue_name=u'metric-batch-workers', countdown=2, method=u'POST', 
        params={u'work_key':work_key})
    except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstoneError):
      pass


class MetricWork(db.Model): 
  # @@TODO: Split this into SumMetricWork and CountMetricWork so count metrics 
  #         can benefit from a smaller entity size.

  #_use_cache = False
  _use_memcache = False

  work_key = db.StringProperty()
  delta = db.IntegerProperty(required=True)

  @classmethod
  def delta_from_work_key(cls, work_key, is_sum=False):
    # @@TODO: Find a way to safely/easily count/sum more than 1000 records in a batch.
    res = cls.query().filter(cls.work_key == work_key).fetch(1000)
    if not len(res):
      utils.log.warn(u'delta_from_work_key got 0 results using work_key: '
        u'%s' % work_key)
    return len(res) if is_sum == False else sum(res)

class TaskMetricSpawnWorkBatchHandler(bolognium.ext.request_handler.TaskRequestHandler):
  @property
  def task_name(self):
    return self.request.headers.get(u'X-AppEngine-TaskName', None)

  @property
  def name(self):
    return self.request.get(u'name', None)

  def get_batch_index_create_lock(self):
    c = memcache.Client()
    mc_key = u'/WORKING_TASK/%s' % self.name
    res = c.gets(mc_key)
    if res == 0:
      return c.cas(u'/WORKING_TASK/%s' % self.name, self.task_name, time=10)
    elif not res:
      return memcache.add(u'/WORKING_TASK/%s' % self.name, self.task_name, time=10)

  def cleanup(self, failed=False):
    client = memcache.Client()
    if client.gets(u'/WORKING_TASK/%s' % self.name) == self.task_name:
      client.cas(u'/WORKING_TASK/%s' % self.name, 0)
    memcache.set(u'/WORKING_SIGNAL/%s' % self.task_name, 
      u'DONE' if not failed else u'FAILED', time=5)

  def signal_batch_index_working(self):
    mc_key = u'/WORKING_SIGNAL/%s' % self.task_name
    return memcache.incr(mc_key, initial_value=0)

  def confirm_batch_index_create_lock(self, relock_if_broken=False):
    locked_task_name = memcache.get(u'/WORKING_TASK/%s' % self.name)
    if locked_task_name:
      if locked_task_name == self.task_name:
        return True
    elif relock_if_broken == True:
      if self.get_batch_index_create_lock():
        return True
    return False

  def ms_elapsed(self):
    td = datetime.datetime.now() - self._start_time
    return int(td.days*86400000 + td.seconds*1000 + td.microseconds/1000)

  @context.toplevel
  def post(self, *args, **kwargs):
    self._start_time = datetime.datetime.now()
    utils.log.info(u'START OF SPAWN WORK BATCH HANDLER############## %dms elapsed.' % self.ms_elapsed())
    if self.name and self.task_name:
      if self.get_batch_index_create_lock():
        @tasklets.tasklet
        def txn():
          res = self.do_work().get_result()
          raise tasklets.Return(res)

        transaction_result = model.transaction_async(txn, retry=0)
        utils.log.info(u'transaction_result: %s. %dms elapsed.' % (transaction_result.get_result(), self.ms_elapsed()))
        #if _s_m.done() and _m_d.done():
        #utils.log.info(u'async_put complete!.' % self.ms_elapsed())
        #WriteLock(u'%s-%d' % (self.name, b_index), lock_on_init=False).spawn_lock()
        #SequenceMarker.update_batch_index_in_memcache(self.name, change_to=b_index, change_from=None)
        #self.cleanup()
        #SequenceMarker.trigger_close_batch_work_task(u'%s-%d' % (self.name, b_index))
      else:
        utils.log.info(u'Could not get lock for batch index creation! %dms elapsed.' % self.ms_elapsed())
    else:
      utils.log.info(u'Missing name or task_name! name: %s, task_name: %s' 
        % (self.name, self.task_name))

  @tasklets.tasklet
  def do_work(self):
    utils.log.info(u'Loading metric_data... %dms elapsed.' % self.ms_elapsed())
    metric_data = MetricData.get_by_id_async(self.name).get_result()
    if not metric_data:
      metric_data = MetricData(id=self.name)
      utils.log.info(u'Created new metric_data! %dms elapsed.' % self.ms_elapsed())
    else:
      utils.log.info(u'Loaded metric_data from datastore! %dms elapsed.' % self.ms_elapsed())
    #The next batch index, and the new 'metric_data.last_created' property 
    #are are obviously equal to the previous 'metric_data.last_created' +1.

    metric_data.last_created = b_index = metric_data.last_created+1
    sequence_marker = SequenceMarker(parent=metric_data.key, i=b_index)

    utils.log.info(u'New Sequence Marker: %s.' % sequence_marker)

    utils.log.info(u'Enqueuing SequenceMarker and MetricData async put. %dms elapsed.' % self.ms_elapsed())
    _s_m = sequence_marker.put_async()
    _m_d = metric_data.put_async()
    utils.log.info(u'Enqueued. %dms elapsed.' % self.ms_elapsed())
    utils.log.info(u'_s_m.done(): %s. %dms elapsed.' % (_s_m.done(), self.ms_elapsed()))
    utils.log.info(u'_m_d.done(): %s. %dms elapsed.' % (_m_d.done(), self.ms_elapsed()))
    loop_i = 0
    while not _s_m.done() or not _m_d.done():
      loop_i += 1
      utils.log.info(u'Within \'while not _s_m.done() or not _m_d.done()\' loop_i: %s. %dms elapsed.' % (loop_i, self.ms_elapsed()))
      if self.ms_elapsed() > 5000:
        utils.log.error(u'Lock took too long! %dms elapsed.' % self.ms_elapsed())
        self.cleanup(failed=True)
        return
      else:
        if self.confirm_batch_index_create_lock(relock_if_broken=True):
          utils.log.info(u'Got the lock.')
          #There was no conflict with other tasks trying to perform the 
          #same work, so signal that everything is ok.
          #self.signal_batch_index_working()
          #time.sleep(.005)
          yield tasklets.sleep(0.02) 
          utils.log.info(u'Immediately after yield tasklets.sleep(0.01).')
        else:
          utils.log.info(u'Lock failed on confirmation!. %dms elapsed.' % self.ms_elapsed())
          #a memcache failure has resulted in the lock being deleted 
          #at just the right time for a sibling task to jump in before 
          #it could be refreshed. This is not common and the easiest way 
          #to deal with it is to yeild to whichever task has the lock.
          self.cleanup(failed=True)
          raise db.Rollback()
    raise tasklets.Return([_s_m, _m_d])


class TaskMetricCloseWorkBatchHandler(bolognium.ext.request_handler.TaskRequestHandler):
  def post(self, *args, **kwargs):
    # First, incr the memcache sequence marker so a new index is spawned.
    work_key = self.request.get(u'work_key')
    name = u'-'.join(work_key.split(u'-')[:-1])
    index = int(work_key.split(u'-')[-1])
    SequenceMarker.update_sequence_info_in_memcache(work_key, 
      change_from=u'%d:2' % index, change_to=None)
    MetricData.trigger_batch_work_task(work_key)

class TaskMetricApplyWorkBatchHandler(bolognium.ext.request_handler.TaskRequestHandler):
  def post(self, *args, **kwargs):
    work_key = self.request.get(u'work_key')
    name = u'-'.join(work_key.split(u'-')[:-1])
    index = int(work_key.split(u'-')[-1])
    WriteLock(work_key).break_locks()    
    delta = MetricWork.delta_from_work_key(work_key)
    def txn():
      metric_data = MetricData.get_by_id_async(name)
      sequence_marker = SequenceMarker.get_by_id_async(work_key)
      metric_data, sequence_marker = yield metric_data, sequence_marker
      if not metric_data or not sequence_marker:
        utils.log.error(u'\'Apply Work Batch\' task didn\'t get metric_data '
          u'or sequence marker.')
        raise SequenceError()
      #apply the delta
      metric_data.delta += delta
      #mark the sequence marker as applied
      sequence_marker.applied = True
      #save the delta on the sequence marker for debugging
      sequence_marker.delta = delta
      #updated the latest applied sequence on the metric data
      metric_data.latest_applied = sequence_marker.i
      #put both objects back
      metric_data.put_async()
      sequence_marker.put_async()
    #run the transaction
    db.transaction(txn, retry=3)

def insert_work_with_custom_retries(retries, name, delta, parent=None):
  for x in xrange(retries):
    try:
      #insert_work(name, **kwargs)
      insert_work(name=name, delta=delta, parent=parent)
    except Exception, e:
      raise
      utils.log.warn(u'Exception inserting work. Retries %d. MSG: %s' 
        % (x, e))
      if x > retries:
        utils.log.warn(u'\'Insert work\' failing after %d retries. MSG: %s' 
          % (x, e))
        raise InsertWorkError(u'Locking failed during work insert. MSG: %s' 
          % e)
    return True

def insert_work(name, delta, parent=None):
  #get a writer lock on a batch sequence
  utils.log.info(u'INSERT WORK NAME##############: %s' % name)
  w_lock = SequenceMarker.get_batch_index_lock(name)
  utils.log.info(u'GOT LOCK ON BATCH INDEX!##############: %s' % w_lock._name)
  return
  #Insert the work
  #yield MetricWork(parent=parent, work_key=w_lock._name, delta=delta).put_async()

  #Confrim the lock.
  #w_lock.lock() 

class WriteLock(object): #rewrite lock
  def __init__(self, name, lock_on_init=True):
    assert isinstance(lock_on_init, bool)
    self._lock_on_init = lock_on_init
    self._locked = False
    self._name = name
    if self._lock_on_init:
      self.lock()      

  @property
  def lock_name(self):
    return u'/WRITE_LOCK/%s' % self._name

  def unlock(self):
    if self._locked:
      memcache.decr(self.lock_name)
      self._locked = False

  def lock(self):
    if self._locked:
      self.unlock()
    self._lock()

  def _lock(self):
    # Get a write lock for this batch sequence position
    lock_val = memcache.incr(self.lock_name)
    if lock_val:
      if lock_val >= 2**16:
        self._locked = True
        return True
      self.unlock()
    raise WriteLockFailedError(u'Write lock \'%s\' failed.' % self.lock_name)

  def spawn_lock(self):
    memcache.set(self.lock_name, 2**16)

  def break_locks(self):
    memcache.delete(self.lock_name)

class Error(Exception):
  pass

class WriteLockFailedError(Exception):
  pass

class SequenceError(Exception):
  pass

class StorageError(Error):
  pass

class AlreadyExistsError(Error):
  pass

class BadArgumentsError(Error):
  pass

class InsertWorkError(Error):
  pass

class InvalidPeriodError(Error):
  pass
