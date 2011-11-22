#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import TaskRequestHandler
from bolognium.ext.metrics import TaskMetricSpawnWorkBatchHandler, \
  TaskMetricCloseWorkBatchHandler, TaskMetricApplyWorkBatchHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db
from google.appengine.api import memcache
import logging, time, datetime

class TaskPurgeModelHandler(TaskRequestHandler):
  def post(self, id, *args, **kwargs):
    id = db.valid_string_id_or_none(id)
    cls = db.model_dict.get(id) if id else None
    if cls:
      to_delete = []
      delete_count = 0
      limit = 100
      res, c, more = cls.query().fetch_page_async(limit, 
        keys_only=True).get_result()
      for r in res:
        r.delete_async()
      delete_count += len(res)
      while more:
        to_delete, c, more = cls.query().fetch_page_async(limit, 
          keys_only=True, start_cursor=c).get_result()
        for r in to_delete: yield r.delete_async()
        delete_count += len(to_delete)
      utils.log.debug('Deleted %s entities of Kind: \'%s\'.' 
        % (delete_count, cls.kind()))

class TaskFlowerEventsHandler(TaskRequestHandler):
  @utils.log_timing
  def post(self, id=None, *args, **kwargs):
    id = db.valid_id_or_default(id, None)
    if not id:
      more = True
      page = 0
      limit = 100
      c = None
      while more:
        res, c, more = db.GatewayHit.has_unflowered_events().\
          fetch_page(limit, start_cursor=c)
        for result in res:
          db.transaction_async(result.flower_event, retry=3, 
            entity_group=result.key)
    else:
      _view_keys = db.MaterializedViewKey.all_recording_enabled().fetch(500)
      def txn():
        gw_hit = db.GatewayHit.get_by_id(id)
        if gw_hit:
          gw_hit.flower_events(_view_keys)
      db.transaction(txn, retry=1, entity_group=db.model.Key(u'GatewayHit', id))

class TaskCountWorkHandler(TaskRequestHandler):
  def post(self, id=None, *args, **kwargs):
    task_name = self.request.headers.get(u'X-AppEngine-TaskName')
    try:
      task_name_parts  = task_name.split(u'-')
      count_name = u'-'.join(task_name_parts[:6])
      event_code = int(task_name_parts[1])
      time_key = task_name_parts[2:6]
      index = int(task_name_parts[-1])

      #the hash of all the 'view_keys', without event code or timestamp
      view_keys_hash = task_name_parts[0]

    except ValueError, e:
      raise
    
    # force new writers to use the next index
    memcache.incr('/COUNT_INDEX/-' + count_name)
    lock = '%s-lock-%d' % (count_name, index)
    memcache.decr(lock, 2**15) # You missed the boat
    # busy wait for writers
    for i in xrange(20): # timeout after 5s
      counter = memcache.get(lock)
      if counter is None or int(counter) <= 2**15:
        break
      time.sleep(0.250)

    work_index = '%s-%d' % (count_name, index)
    results = db.IncrementWork.work_by_index(work_index)
    to_add = len(results)
    def txn():
      materialized_view = db.MaterializedView.get_by_id(count_name)
      if materialized_view is None:
        view_keys = [db.ViewKey(name=_name,value=_value) \
          for _name,_value in utils.json.loads(results[0].work_data).iteritems()]
        date_time_key = datetime.datetime(*[int(x) for x in time_key])
        materialized_view = db.MaterializedView(id=count_name, \
          view_keys=view_keys, view_keys_hash=view_keys_hash, 
          event=event_code, count=0, time_key=date_time_key)
      materialized_view.count += to_add
      materialized_view.put_async()

    #run the transaction
    db.delete_async(results)
    db.transaction(txn, retry=3)

class TaskPrepareModelHandler(TaskRequestHandler):
  def post(self, id=None, *args, **kwargs):
    _dict = db.model_dict
    model_class = _dict.get(model.string_or_default(id, default=u''))
    if model_class is None:
      raise Exception(u'Model %s not found' % model_name)
    if hasattr(model_class, u'_prepare'):
      model_class._prepare()
    
    
