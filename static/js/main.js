goog.provide('app');
goog.provide('app.is_debug');
goog.provide('app.images');
goog.provide('app.events.startLoadingEvent');
goog.provide('app.events.endLoadingEvent');
goog.provide('app.fx.CustomDragger');
goog.provide('app.net.XhrIo');
goog.provide('app.net.RpcRequest');
goog.provide('app.ui.Dialog');
goog.provide('app.ui.editor');
goog.provide('app.ui.editor.plugins');
goog.provide('app.ui.editor.plugins.ImageDialog.events');
goog.provide('app.ui.editor.plugins.ImageDialog.events.imgReady');
goog.provide('app.ui.editor.plugins.ImageDialog.createAcceptOrCropButtonSet');
goog.provide('app.ui.editor.plugins.ImageDialog.OkEvent');
goog.provide('app.ui.editor.plugins.ImageDialogPlugin');
goog.provide('app.ui.editor.plugins.CodeDialogPlugin');
goog.provide('app.ui.editor.plugins.HeaderFormatter');
goog.provide('app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND');
goog.provide('app.ui.editor.plugins.CodeDialog');
goog.provide('app.ui.editor.plugins.ImageBubble');
goog.provide('app.ui.ImgPickerDialog');

goog.provide('app.db.ImgSelector');
goog.provide('app.db.ImgEditor');
goog.provide('app.db.ImgEditor.events');
goog.provide('app.db.ImgEditor.events.ImgEditFinished');

goog.require('goog.dom');
goog.require('goog.dom.DomHelper');
goog.require('goog.dom.TagName');
goog.require('goog.style');
goog.require('goog.json');
goog.require('goog.dom.forms');
goog.require('goog.array');
goog.require('goog.Timer');
goog.require('goog.math');
goog.require('goog.math.Integer');
goog.require('goog.math.Coordinate');
goog.require('goog.object');
goog.require('goog.functions');
goog.require('goog.events');
goog.require('goog.events.EventType');
goog.require('goog.ui.Dialog');
goog.require('goog.string');
goog.require('goog.net.XhrIo');
goog.require('goog.net.IframeIo');
goog.require('goog.ui.ProgressBar');
goog.require('goog.ui.editor.DefaultToolbar');
goog.require('goog.ui.editor.ToolbarController');
goog.require('goog.ui.editor.AbstractDialog');
goog.require('goog.ui.editor.AbstractDialog.EventType');
goog.require('goog.ui.editor.messages');
goog.require('goog.editor.Command');
goog.require('goog.editor.Field');
goog.require('goog.editor.plugins.AbstractBubblePlugin');
goog.require('goog.editor.plugins.BasicTextFormatter');
goog.require('goog.editor.plugins.TagOnEnterHandler');
goog.require('goog.editor.plugins.HeaderFormatter');
goog.require('goog.editor.plugins.LinkBubble');
goog.require('goog.editor.plugins.LinkDialogPlugin');
goog.require('goog.editor.plugins.ListTabHandler');
goog.require('goog.editor.plugins.LoremIpsum');
goog.require('goog.editor.plugins.RemoveFormatting');
goog.require('goog.editor.plugins.SpacesTabHandler');
goog.require('goog.editor.plugins.UndoRedo');
goog.require('goog.editor.plugins.AbstractDialogPlugin');
goog.require('goog.editor.range');



/**
 * Array of all images known to the client, by their IDs.
 * type {array}
 * @private
 */
app.db.ImgRegistry = {};
app.configVars_ = _app_config || {};
app.getConfig = function(opt_name) {
  if(goog.object.containsKey(app.configVars_, opt_name)) {
    return app.configVars_[opt_name];
  }
  return;
}
app.is_debug = function() {
  //returns false if debug is set to any value other than true.
  return app.getConfig('debug') === true ? true : false;
}

/**
 * The base class for our implementation of various I/O related functionality.
 * type {Constructor}
 * @public
 */
app.net.XhrIo = function(opt_xmlHttpFactory) {
  goog.net.XhrIo.call(this);
  //goog.base(this);
}
goog.inherits(app.net.XhrIo, goog.net.XhrIo);

/**
 * The base class for our RPC specific I/O stuff.
 * type {Constructor}
 * @public
 */
app.net.RpcRequest = function(opt_method_name, opt_method, opt_params, opt_xmlHttpFactory) {
  this.methodName_ = opt_method_name;
  this.params_ = opt_params;
  this.method_ = opt_method;
  this.url_ = '/rpc/' + this.methodName_;
  app.net.XhrIo.call(this);
  //goog.base(this);
}
goog.inherits(app.net.RpcRequest, app.net.XhrIo);

app.net.RpcRequest.prototype.run = function() {
  var params, request_method, content, opt_headers = null;
  if (this.method_.toUpperCase() == 'POST') {
    request_method = 'POST';
  } else {
    request_method = 'GET';
  }
  content = 'params=' + goog.json.serialize(this.params_);
  opt_headers = {};
  return this.send(this.url_, request_method, content, opt_headers);
}

app.net.RpcRequest.prototype.url_ = null;
app.net.RpcRequest.prototype.method_ = null;
app.net.RpcRequest.prototype.methodName_ = null;
app.net.RpcRequest.prototype.params_ = null;


app.startEditorOnField = function(field_elem, form_elem, contents) {
  var field_elem = goog.dom.getElement(field_elem);
  var form_elem = goog.dom.getElement(form_elem);
  var field = new goog.editor.Field(field_elem.id, goog.dom.getDomHelper(field_elem));
  field.registerPlugin(new goog.editor.plugins.BasicTextFormatter());
  field.registerPlugin(new goog.editor.plugins.RemoveFormatting());
  field.registerPlugin(new goog.editor.plugins.ListTabHandler());
  field.registerPlugin(new goog.editor.plugins.SpacesTabHandler());
  field.registerPlugin(new app.ui.editor.plugins.HeaderFormatter());
  field.registerPlugin(new goog.editor.plugins.LinkDialogPlugin());
  field.registerPlugin(new app.ui.editor.plugins.ImageBubble());
  field.registerPlugin(new app.ui.editor.plugins.ImageDialogPlugin());
  field.registerPlugin(new app.ui.editor.plugins.CodeDialogPlugin());

  var buttons = [
    goog.editor.Command.FONT_COLOR,
    goog.editor.Command.BOLD,
    goog.editor.Command.ITALIC,
    goog.editor.Command.UNDERLINE,
    goog.editor.Command.LINK,
    goog.editor.Command.UNORDERED_LIST,
    goog.editor.Command.ORDERED_LIST,
    goog.editor.Command.INDENT,
    goog.editor.Command.OUTDENT,
    goog.editor.Command.SUBSCRIPT,
    goog.editor.Command.SUPERSCRIPT,
    goog.editor.Command.STRIKE_THROUGH,
    goog.editor.Command.IMAGE,
    goog.ui.editor.ToolbarFactory.makeButton('code', "Add Code Snippet", "code")
  ];
  var toolbar = goog.ui.editor.DefaultToolbar.makeToolbar(buttons,
    goog.dom.getElement(field_elem.id+'-toolbar')
  );

  // Hook the toolbar into the field.
  var myToolbarController = new goog.ui.editor.ToolbarController(field, toolbar);
  field.makeEditable();
  if(contents) {
    field.setHtml(true, contents);
  }
  goog.events.listen(form_elem, goog.events.EventType.SUBMIT, function(e) {
    this.makeUneditable();
  }, false, field);
}

//********************** {Object} app.ui.Dialog *********************************************************//
/**
 * The base dialog class
 * @constructor
 * @extends {goog.ui.Dialog}
 */
app.ui.Dialog = function(ctx_opts, opt_class, opt_useIframeMask, opt_domHelper) {
  goog.base(this, opt_class, opt_useIframeMask, opt_domHelper);
  this.updateCtxOpts(ctx_opts);
  this.eventHandler_ = new goog.events.EventHandler(this);
  this.load();
  this.setVisible(true);
  //goog.ui.Dialog.call(this, opt_class, opt_useIframeMask, opt_domHelper);
}
goog.inherits(app.ui.Dialog, goog.ui.Dialog);

/**
 * The Context Options Object.
 * @public
 */
app.ui.Dialog.prototype.ctxOpts_ = {};

/**
 * The Context Options Object.
 * @public
 */
app.ui.Dialog.prototype.getCtxOpt = function(opt_name, default_value) {
  return goog.object.get(this.ctxOpts_, opt_name, default_value || null);
}

/**
 * Set the Context Options object.
 * @public
 */
app.ui.Dialog.prototype.updateCtxOpts = function(new_opts, set) {
  if (set === true) {
    //we must delete old ctxOpts and use only these new ones
    this.ctxOpts_ = new_opts;
  } else {
    goog.object.forEach(new_opts, function(val, k) {
      this.ctxOpts_[k] = val;
    }, this);
  }
}

/**
 * Clear the dialog.
 * @public
 */
app.ui.Dialog.prototype.clear = function() {
  goog.dom.removeChildren(this.getContentElement());
}
/**
 * Set the dialog size.
 * @param {integer} width The new width.
 * @param {integer} height The new height.
 * @public
 */
app.ui.Dialog.prototype.setSize = function(width, height) {
  var contentElem_ = this.getContentElement();
  goog.style.setStyle(contentElem_, 'width', width + 'px');
  goog.style.setStyle(contentElem_, 'height', height + 'px');
  this.reposition();
}

/**
 * Runs as a function of setup and then later during 'reload()', etc.
 * @param {Object} ctx_opts Contextual Options for the Dialog.
 * @private
 */
app.ui.Dialog.prototype.load = function(ctx_opts) {
}


//********************** {Object} Loading Animation *********************************************************//
/**
 * Image Picker Dialog
 */
app.ui.ImgPickerDialog = function(ctx_opts, opt_class, opt_useIframeMask, opt_domHelper) {
  goog.base(this, ctx_opts, opt_class, opt_useIframeMask, opt_domHelper || this.getDomHelper());
}
goog.inherits(app.ui.ImgPickerDialog, app.ui.Dialog);

/**
 * Image Picker load()
 */
app.ui.ImgPickerDialog.prototype.load = function() {
  var imgSelector_ = new app.db.ImgSelector(this.getDomHelper());
  this.setTitle('Choose An Image');
  this.setButtonSet(new goog.ui.Dialog.ButtonSet().addButton(goog.ui.Dialog.ButtonSet.DefaultButtons.CANCEL, false, true));
  goog.dom.append(this.getContentElement(), imgSelector_.buildUploadImageElement_());
  //listen for the ImgSelector's 'imgselected' and let returnImg_ dispatch 
  //the approprate event and close down thhe dialog.
  this.eventHandler_.listen(imgSelector_, 'imgselected', function(e) {
    this.returnImg_(e.selectedImg_);
  }, false, this);

  //listen for the event that indicates loading process, and trigger UI behaviour
  this.eventHandler_.listen(imgSelector_, 'startloading', function(e) {
    goog.dom.removeChildren(this.getContentElement());
    this.progress_ = new app.ui.ProgressAnimation(e.msg_);
    goog.dom.append(this.getContentElement(), this.progress_.getElement());
    this.progress_.startAnimation();
  }, false, this);
  //~ this.setVisible(true);
};

/**
 * Image Picker Dialog
 */
app.ui.ImgPickerDialog.prototype.returnImg_ = function(img_to_return) {
  this.dispatchEvent(new goog.events.Event(app.ui.ImgPickerDialog.events.IMG_PICKED, img_to_return));
}

/**
 * Image Picker Dialog
 */
app.ui.ImgPickerDialog.events = {
  IMG_PICKED: 'imgpicked'
};


//********************** {Object} Loading Animation *********************************************************//
/**
 * A 'loading' animation object.
 * @param {Object}
 * @param {string} message The message to display while loading.
 * @constructor
 * @extends {goog.ui.ProgerssBar}
 */
 
app.ui.ProgressAnimation = function(message, container) {
  goog.ui.ProgressBar.call(this);
  this.setMessage(message);
  var elem = goog.dom.createDom('div',{'id': 'uploader-progress-bar', 'class': 'progress-bar-container'});
  goog.dom.appendChild(elem, goog.dom.createDom('div', {'class': 'progress-bar-thumb'}));
  goog.dom.appendChild(elem, goog.dom.createDom('div', {'class': 'progress-bar-text'}, this.getMessage()));
  this.setElement(elem);
  this.decorate(elem);
  if(container) {
    goog.dom.appendChild(elem, container);
    this.startAnimation();
  }
}
goog.inherits(app.ui.ProgressAnimation, goog.ui.ProgressBar);

/**
 * Starts the animation if it isn't started already.
 * @public
 */
app.ui.ProgressAnimation.prototype.startAnimation = function() {
  if (this.getStarted() === true) {
    return;
  }
  var t = new goog.Timer(50);
  var last = 0;
  var delta = 5;
  t.addEventListener('tick', function(e) {
    if (last > 100 || last < 0) {
      delta = -delta;
    }
    last += delta;
    this.setValue(last);
  }, null, this);
  t.start();
  this.setStarted(true);
}

/**
 * Has the animation been started?
 * @type {Boolean}
 * @private
 */
app.ui.ProgressAnimation.prototype.started_ = false;

/**
 * Returns 'started' value
 * @public
 */
app.ui.ProgressAnimation.prototype.getStarted = function() {
  return this.started_;
}
/**
 * Sets 'started' value to true.
 * @public
 */
app.ui.ProgressAnimation.prototype.setStarted = function(started) {
  this.started_ = started;
}

/**
 * The message text string.
 * @type {String}
 * @private
 */
app.ui.ProgressAnimation.prototype.message_;
/**
 * Sets the message string
 * @param {String} message The message string.
 * @public
 */
app.ui.ProgressAnimation.prototype.setMessage = function(message) {
  this.message_ = message;
}
/**
 * Gets the message string
 * @public
 */
app.ui.ProgressAnimation.prototype.getMessage = function() {
  return this.message_ || 'Loading...';
}

/**
 * The loading animation element.
 * @private
 */
app.ui.ProgressAnimation.prototype.element_;

/**
 * Sets the loading animation element.
 * @param {Object} element The Element.
 * @public
 */
app.ui.ProgressAnimation.prototype.setElement = function(element) {
  this.element_ = element;
}
/**
 * Gets the loading animation element.
 * @public
 */
app.ui.ProgressAnimation.prototype.getElement = function() {
  return this.element_;
}

//************** {Object} app.db.ImgSelector  **************************************/
/**
 * The Image Selector Class
 * Provides an interface to fetch or upload images,
 * or choose from previously fetched or uploaded images.
 * @constructor
 * @extends {goog.events.EventTarget}
 */
app.db.ImgSelector = function(opt_domHelper) {
  goog.base(this, this.dom);
  goog.events.EventTarget.call(this)
  this.dom = opt_domHelper || goog.dom.createDom();
  this.eventHandler_ = new goog.events.EventHandler(this);
}
goog.inherits(app.db.ImgSelector, goog.events.EventTarget);

//************** {Object} app.db.ImgSelector.Id_ **************************************/
/**
 * IDs for relevant DOM elements.
 * @enum {string}
 * @private
 */
app.db.ImgSelector.Id_ = {
  FETCH_INPUT: 'imageselector-fetch-input',
  FETCH_FORM: 'imageselector-fetch-form',
  FETCH_SUBMIT: 'imageselector-fetch-submit',
  UPLOAD_INPUT: 'imageselector-upload-input',
  UPLOAD_FORM: 'imageselector-upload-form'
}

//************** {function} app.db.ImgSelector.prototype.getEventHandler ***************/
/**
 * Sets EventHandler_ for this object.
 * @param {Object} eventHandler An eventHandler Object.
 * @public
 */
app.db.ImgSelector.prototype.getEventHandler = function() {
  return this.eventHandler_;
}

//************** {function} app.db.ImgSelector.prototype.dom ***************/
/**
 * The domHelper object.
 * @public
 */
app.db.ImgSelector.prototype.dom = null;

//************** {function} app.db.ImgSelector.prototype.onUploadImageInputChange_ ***************/
/**
 * Handles CHANGE event on the upload file input.
 * @param {Object} e The mousedown event object.
 * @param {String} corner The corner beign activated. e.g. 'NE'.
 * @private
 */
app.db.ImgSelector.prototype.onUploadImageInputChange_ = function() {
  this.dispatchEvent(new app.events.startLoadingEvent('Uploading...'));
  var url_io = new goog.net.IframeIo();
  this.eventHandler_.listen(url_io, goog.net.EventType.COMPLETE, function(e) {
    var response = e.target;
    if (response.isSuccess()) {
      var response_data = goog.json.unsafeParse(response.getResponseText());
      var form = this.dom.getElement(app.db.ImgSelector.Id_.UPLOAD_FORM);
      this.fileForm_.action = response_data.upload_url;
      var io = new goog.net.IframeIo();
      this.eventHandler_.listen(io, goog.net.EventType.COMPLETE, this.handleImageFromServer_);
      io.sendFromForm(this.fileForm_);
      this.fileForm_ = null;
    }  else {
      _logger.log("ERROR ON UPLOAD URL GET. MSG: " + response.error_msg);
    }
  }, false, this);
  url_io.send('/image/get-upload-url');
}

//************** {function} app.db.ImgSelector.prototype.onFetchImageSubmit_ ***************/
/**
 * Handles CHANGE event on the upload file input.
 * @param {Object} e The mousedown event object.
 * @param {String} corner The corner beign activated. e.g. 'NE'.
 * @private
 */
app.db.ImgSelector.prototype.onFetchImageSubmit_ = function(e) {
  e.preventDefault();
  var io = new goog.net.IframeIo(); 
  var form = this.dom.getElement(app.db.ImgSelector.Id_.FETCH_FORM);
  this.eventHandler_.listen(io, goog.net.EventType.COMPLETE, this.handleImageFromServer_);
  io.sendFromForm(form); 
  this.dispatchEvent(new app.events.startLoadingEvent('Fetching...'));
}

//************** {function} buildFetchImageElement_() **************************************/
/**
* Builds and returns the div containing the tab "On the web".
* @return {Element} The div element containing the element structure.
* @private
*/
app.db.ImgSelector.prototype.buildFetchImageElement_ = function() {
  var onTheWebDiv = this.dom.createElement(goog.dom.TagName.DIV);

  var table = this.dom.createTable(2, 1);
  table.cellSpacing = '0';
  table.cellPadding = '0';

  // Heading
  var heading = this.dom.createDom('h3', {}, this.dom.createDom('span', {}, 'From Url'))
  goog.dom.appendChild(table.rows[0].cells[0], heading)

  var urlInput = this.dom.createDom(goog.dom.TagName.INPUT,
      {id: app.db.ImgSelector.Id_.FETCH_INPUT,
       name: 'image_url',
       type: 'text'});

  var urlForm = this.dom.createDom(goog.dom.TagName.FORM,
      {id: app.db.ImgSelector.Id_.FETCH_FORM,
       method: 'post',
       action: '/image/add',
       onsubmit: 'return false'});

  urlForm.appendChild(urlInput);

  var urlSubmit = this.dom.createDom(goog.dom.TagName.INPUT,
      {id: app.db.ImgSelector.Id_.FETCH_SUBMIT,
       type: 'submit',
       value: 'Fetch'});

  urlForm.appendChild(urlSubmit);

  goog.style.setStyle(urlInput, 'width', '370px');
  goog.style.setStyle(urlSubmit, 'width', '80px');
  goog.style.setStyle(table, 'margin-bottom', '15px');
  goog.dom.appendChild(table.rows[1].cells[0], urlForm);

  this.getEventHandler().listen(urlForm, goog.events.EventType.SUBMIT,
      this.onFetchImageSubmit_);

  onTheWebDiv.appendChild(table);

  return onTheWebDiv;
};

//************** {function} buildUploadImageElement_() **************************************/
/**
* Builds and returns the div containing the upload form.
* @return {Element} The div element containing the element structure.
* @private
*/
app.db.ImgSelector.prototype.buildUploadImageElement_ = function() {
  var uploadDiv = this.dom.createElement(goog.dom.TagName.DIV);

  var table = this.dom.createTable(2, 1);
  table.cellSpacing = '0';
  table.cellPadding = '0';

  // Build the text to display input.
  var heading = this.dom.createDom('h3', {}, this.dom.createDom('span', {}, 'Upload'))
  goog.dom.appendChild(table.rows[0].cells[0], heading)

  var fileInput = this.dom.createDom(goog.dom.TagName.INPUT,
      {id: app.db.ImgSelector.Id_.UPLOAD_INPUT,
       type: 'file',
       name: 'image'});

  this.fileForm_ = this.dom.createDom(goog.dom.TagName.FORM,
      {id: app.db.ImgSelector.Id_.UPLOAD_FORM,
       method: 'post',
       action: '/image/add',
       enctype: 'multipart/form-data',
       onsubmit: 'return false'});

  this.fileForm_.encoding = 'multipart/form-data'; // fix for IE

  this.fileForm_.appendChild(fileInput);

  goog.style.setStyle(this.fileForm_, 'width', '98%');
  goog.style.setStyle(table.rows[1].cells[0], 'width', '100%');
  goog.style.setStyle(table, 'margin-bottom', '15px');
  goog.dom.appendChild(table.rows[1].cells[0], this.fileForm_);

  this.getEventHandler().listen(fileInput, goog.events.EventType.CHANGE, this.onUploadImageInputChange_);

  uploadDiv.appendChild(table);
  return uploadDiv;
};

app.db.ImgSelector.prototype.fileForm_ = null;

//************** {function} handleImageFromServer_ **************************************/
/**
 * Handles image data returned from the server.
 * @private
 */
app.db.ImgSelector.prototype.handleImageFromServer_ = function(e) {
  var response = e.target;
  if (response.isSuccess()) {
    var response_data = response.getResponseJson();
    img = new app.db.Img(response_data);
    _logger.log(img);
    goog.events.dispatchEvent(this, new app.events.endLoadingEvent());
    this.dispatchEvent(new app.db.ImgSelector.imgSelectedEvent(img));
  }  else {
    _logger.log("ERROR ON IMAGE GET. MSG: " + response.error_msg);
  }
}

//************** {Object} app.db.ImgSelector.prototype.eventHandler_ **************************************/
/**
 * EventHandler object that keeps track of all handlers set by the ImgSelector.
 * @type {goog.events.EventHandler}
 * @private
 */
app.db.ImgSelector.prototype.eventHandler_;

//************** {Object} app.db.ImgSelector.prototype.urlInputHandler_ **************************************/
/**
 * InputHandler object to listen for changes in the url input field.
 * @type {goog.events.InputHandler}
 * @private
 */
app.db.ImgSelector.prototype.urlInputHandler_;

//************** {Object} loadingStartEvent_ Event **************************************/
/**
 * Event to signal the START of a trip to the server for something.
 * @param {string} ANYTHING?!?!
 * @constructor
 * @extends {goog.events.Event}
 */
app.events.startLoadingEvent = function(msg) {
  this.type = 'startloading';
  if (msg) {
    this.msg_ = msg;
  }
  goog.events.Event.call(this, this.type);
};
goog.inherits(app.events.startLoadingEvent, goog.events.Event);

//************** {Object} loadingEndEvent_ Event **************************************/
/**
 * Event to signal the END of a trip to the server for something.
 * @param {string} ANYTHING?!?!
 * @constructor
 * @extends {goog.events.Event}
 */
app.events.startLoadingEvent.prototype.msg_ = 'Loading...';

//************** {Object} loadingEndEvent_ Event **************************************/
/**
 * Event to signal the END of a trip to the server for something.
 * @param {string} ANYTHING?!?!
 * @constructor
 * @extends {goog.events.Event}
 */
app.events.endLoadingEvent = function() {
  this.type = 'endloading';
  goog.events.Event.call(this, this.type)
};
goog.inherits(app.events.endLoadingEvent, goog.events.Event);

//************** {Object} app.db.ImgSelector.ImageSelected Event **************************************/
/**
 * Returns an imgSelectedEvent
 * @param {string} imageUrl Url the image.
 * @constructor
 * @extends {goog.events.Event}
 */
app.db.ImgSelector.imgSelectedEvent = function(img) {
  this.type = 'imgselected';
  this.selectedImg_ = img;
  goog.events.Event.call(this, this.type);
}
goog.inherits(app.db.ImgSelector.imgSelectedEvent, goog.events.Event);

app.db.ImgSelector.imgSelectedEvent.prototype.selectedImg_ = null;


/**
 * The Custom Dragger, for use with the Image Editor
 * @param {Object} target
 * @param {Object} handle
 * @param {Object} limits
 * @constructor
 * @extends {goog.fx.Dragger}
 */
app.fx.CustomDragger = function(target, handle, limits) {
  goog.fx.Dragger.call(this, target, handle, limits);
}
goog.inherits(app.fx.CustomDragger, goog.fx.Dragger);

app.fx.CustomDragger.prototype.defaultAction = function(x, y) {
}



// *** app.db.ImgEditor *********************************************** //
/**
 * The Image Editor Class
 * @param {Object} image THE IMAGE!
 * @param {Object} template_opts Template options if any.
 * @param {int} max_width The max width the viewport can handle.
 * @param {int} max_height The max height the viewport can handle.
 * @constructor
 * @extends {goog.events.EventTarget}
 */
app.db.ImgEditor = function(domHelper) {
  goog.events.EventTarget.call(this);
  this.dom = domHelper || goog.dom.createDom();
  this.eventHandler_ = new goog.events.EventHandler(this);
}
goog.inherits(app.db.ImgEditor, goog.events.EventTarget);


// *** app.db.ImgEditor.prototype.eventHandler_ *********************************************** //
/**
 * The eventHandler_ Object.
 * @type Object
 */
app.db.ImgEditor.prototype.eventHandler_ = null;

// *** app.db.ImgEditor.prototype.width_ *********************************************** //
/**
 * The img being edited.
 * @app.db.Img
 */
app.db.ImgEditor.prototype.img_ = null;

// *** app.db.ImgEditor.prototype.scale_ *********************************************** //
/**
 * The img being edited.
 * @float
 */
app.db.ImgEditor.prototype.scale_ = 1.0;

// *** app.db.ImgEditor.prototype.maxWidth_ *********************************************** //
/**
 * A possible upper limit on the width of the editor.
 * @int
 */
app.db.ImgEditor.prototype.maxWidth_ = null;

// *** app.db.ImgEditor.prototype.maxHeight_ *********************************************** //
/**
 * A possible upper limit on the height of the editor.
 * @int
 */
app.db.ImgEditor.prototype.maxHeight_ = null;

// *** app.db.ImgEditor.prototype.editOpts_ *********************************************** //
/**
 * Optional edit options/config.
 * @int
 */
app.db.ImgEditor.prototype.editOpts_ = null;

// *** app.db.ImgEditor.prototype.cropWindow_ *********************************************** //
/**
 * The crop window.
 * @int
 */
app.db.ImgEditor.prototype.cropWindow_ = null;

// *** app.db.ImgEditor.prototype.draggers_ *********************************************** //
/**
 * An object to contain references to individual handle draggers.
 */
app.db.ImgEditor.prototype.draggers_ = {};

// *** app.db.ImgEditor.prototype.handles_ *********************************************** //
/**
 * An object to contain references to individual handles.
 */
app.db.ImgEditor.prototype.handles_ = {};

// *** app.db.ImgEditor.prototype.cropWindowDragger_ *********************************************** //
/**
 * The current/last app.fx.CustomDragger object.
 * @int
 */
app.db.ImgEditor.prototype.cropWindowDragger_ = null;

// *** app.db.ImgEditor.prototype.cropWindowDragger_ *********************************************** //
/**
 * The current/last editor dom.
 */
app.db.ImgEditor.prototype.editorDom_ = null;

// *** app.db.ImgEditor.prototype.cropWindowWidth_ *********************************************** //
/**
 * The width of the crop window.
 */
app.db.ImgEditor.prototype.cropWindowWidth_ = null;

// *** app.db.ImgEditor.prototype.cropWindowHeight_ *********************************************** //
/**
 * The height of the crop window.
 */
app.db.ImgEditor.prototype.cropWindowHeight_ = null;

// *** app.db.ImgEditor.prototype.bgImage_ *********************************************** //
/**
 * The canvas background image.
 */
app.db.ImgEditor.prototype.bgImage_ = null;

// *** app.db.ImgEditor.prototype.fgImage_ *********************************************** //
/**
 * The canvas foreground image.
 */
app.db.ImgEditor.prototype.fgImage_ = null;

// *** app.db.ImgEditor.prototype.canvasWidth_ *********************************************** //
/**
 * The canvas width.
 */
app.db.ImgEditor.prototype.canvasWidth_ = null;

// *** app.db.ImgEditor.prototype.canvasHeight_ *********************************************** //
/**
 * The canvas height.
 */
app.db.ImgEditor.prototype.canvasHeight_ = null;

// *** app.db.ImgEditor.prototype.canvas_ *********************************************** //
/**
 * The canvas.
 */
app.db.ImgEditor.prototype.canvas_ = null;

// *** Current points *********************************************** //
/**
 * Current points.
 */
app.db.ImgEditor.prototype.NW_pos = null;
app.db.ImgEditor.prototype.NE_pos = null;
app.db.ImgEditor.prototype.SW_pos = null;
app.db.ImgEditor.prototype.SE_pos = null;

//************** {function} app.db.ImgEditor.prototype.dom ***************/
/**
 * The domHelper object.
 * @public
 */
app.db.ImgEditor.prototype.dom = null;

/**
 * Signals end of Editing.
 */
app.db.ImgEditor.prototype.triggerEditFinish_ = function(img) {
  this.dispatchEvent(new app.db.ImgEditor.events.ImgEditFinished(img || this.img_));
};

/**
 * Begins crop process, and signals end of editing after getting the response.
 */
app.db.ImgEditor.prototype.triggerCrop_ = function(e) {
  e.preventDefault();
  this.dispatchEvent(new app.events.startLoadingEvent('Processing...'));
  var crop_rpc = new app.net.RpcRequest('image_crop_and_copy', 'POST', 
    {img_id: img.getId(), crop_args: this.getPoint_('left_x')
    +':'+this.getPoint_('top_y')
    +':'+this.getPoint_('right_x')
    +':'+this.getPoint_('bottom_y')});
  goog.events.listen(crop_rpc, goog.net.EventType.COMPLETE, function(e) {
    var response = e.target;
    var response_data = response.getResponseJson();
    if (response.isSuccess()) {
      _logger.log('Completed the "image_crop_and_copy" RPC.');
      var response_data = response.getResponseJson();
      var updated_gallery = new app.db.Img(response_data['cropped_img']);
      this.dispatchEvent(new app.events.endLoadingEvent());
      this.triggerEditFinish_(this.img_);
    } else {
      _logger.log("Error with the image processing!. MSG: "+ response_data.error_msg);
    }
  }, false, this);
  crop_rpc.run();
};

// *** app.db.ImgEditor.prototype.buildEditor *********************************************** //
/**
 * Builds the editor around an img object.
 * @param {Object} img The app.db.Img object.
 * @param {Object} edit_opts Optional Img editing resictions.
 * @param {Object} domHelper An optional domHelper object.
 */
app.db.ImgEditor.prototype.buildEditor = function(img, edit_opts, max_width, max_height) {
  this.img_ = img;
  this.editOpts_ = edit_opts;
  this.maxHeight_ = max_height || -1;
  this.maxWidth_ = max_width || -1;

  //scale if need be
  var too_wide_factor,too_high_factor = 1;
  var scaled_height,scaled_width = null;
  var too_wide,too_high = false;
  if (this.maxWidth_ > 0 && this.img_.getProperty('width') > this.maxWidth_) {
    too_wide = true;
    too_wide_factor = this.maxWidth_/this.img_.getProperty('width');
  }
  if (this.maxHeight >0 && this.img_.getProperty('height') > this.maxHeight_) {
    too_high = true;
    too_high_factor = this.maxHeight_/this.img_.getProperty('height');
  }
  if(too_wide || too_high) {
    this.scale_ = Math.max(too_high_factor, too_wide_factor);
    scaled_height = this.img_.getProperty('height')*this.scale_;
    scaled_width = this.img_.getProperty('width')*this.scale_;
  }else{
    scaled_height = this.img_.getProperty('height');
    scaled_width = this.img_.getProperty('width');
  }
  
  //maybe we need to dispose of possible old stuff here.
  this.editorDom_ = this.dom.createElement('div');

  this.canvasWidth_ = this.cropWindowWidth_ = this.img_.getProperty('width');
  this.canvasHeight_ = this.cropWindowHeight_ = this.img_.getProperty('height');
  this.canvas_ = this.dom.createDom('div', {'class':'image-editor-canvas', 'style':'width:'+this.canvasWidth_+'px;height:'+this.canvasHeight_+'px;'});
  this.cropWindow_ = this.dom.createDom('div', {'class':'image-editor-crop-window', 'style':'width:'+this.cropWindowWidth_+'px;height:'+this.cropWindowHeight_+'px;'});
  this.bgImage_ = this.dom.createDom('img', {'class':'image-editor-bg-image', 'height': scaled_height, 'width': scaled_width, 'src': this.img_.getProperty('url')});
  this.fgImage_ = this.dom.createDom('img', {'class':'image-editor-fg-image', 'height': scaled_height, 'width': scaled_width, 'src': this.img_.getProperty('url')});

  goog.dom.appendChild(this.canvas_, this.bgImage_);
  goog.dom.appendChild(this.canvas_, this.cropWindow_);
  goog.dom.appendChild(this.cropWindow_, this.fgImage_);
  this.eventHandler_.listen(this.cropWindow_, goog.events.EventType.MOUSEDOWN, function(e) {
    goog.style.setStyle(this.fgImage_, 'opacity', '.8');
    this.cropWindowDragger_ = new app.fx.CustomDragger(this.cropWindow_, null, new goog.math.Rect(0,0,this.canvasWidth_-this.cropWindowWidth_,this.canvasHeight_-this.cropWindowHeight_));
    this.eventHandler_.listen(this.cropWindowDragger_, goog.fx.Dragger.EventType.DRAG, this.handleCropWindowDrag_);
    this.eventHandler_.listen(this.cropWindowDragger_, goog.fx.Dragger.EventType.END, function(e){
      goog.style.setStyle(this.fgImage_, 'opacity', '1');
      this.cropWindowDragger_.dispose();
      this.cropWindowDragger_ = null;
    });
    this.cropWindowDragger_.startDrag(e);
  });
  //append the canvas element and it's children
  goog.dom.appendChild(this.editorDom_, this.canvas_);

  //goog.events.listen(this.finished_button, goog.events.EventType.CLICK, this.handleFinishedButton, false, this);

  var corners = {
    'NW': new goog.math.Coordinate(0,0),
    'NE': new goog.math.Coordinate(this.canvasWidth_,0),
    'SE': new goog.math.Coordinate(this.canvasWidth_, this.canvasHeight_),
    'SW': new goog.math.Coordinate(0,this.canvasHeight_)
  };

  for(var i in corners) {
    var corner = i;
    var pos = corners[i];
    this.handles_[corner] = this.dom.createDom('div', {'class':'image-editor-crop-handle image-editor-crop-handle-'+corner});
    goog.dom.appendChild(this.canvas_, this.handles_[corner]);
    goog.style.setPosition(this.handles_[corner], pos);
    this[corner+'_pos'] = pos;
    this.eventHandler_.listen(this.handles_[corner], goog.events.EventType.MOUSEDOWN, function(e) {
      this.obj.handleCropHandleMouseDown_(e, this.corner);
    }, false, {obj:this, corner:corner});
  }
  this.setCropWindowToRect_(
    new goog.math.Rect(
      this.canvasWidth_-(this.canvasWidth_*.9),
      this.canvasHeight_-(this.canvasHeight_*.9),
      this.canvasWidth_*.8,
      this.canvasHeight_*.8
    )
  );
  return this.editorDom_;
}

/**
 * Gets the pixel coordinate for a specific screen coordinate.
 * @param {String} point The point being translated. e.g. 'left_x'.
 * @private
 */
app.db.ImgEditor.prototype.getPoint_ = function(point) {
  var val = null;
  switch(point) {
    case 'left_x':
    val = (this.getCurrentPos('NW').x/this.scale_)/this.img_.getProperty('width');
    break;
    case 'top_y':
    val = (this.getCurrentPos('NW').y/this.scale_)/this.img_.getProperty('height');
    break;
    case 'right_x':
    val = (this.getCurrentPos('SE').x/this.scale_)/this.img_.getProperty('width');
    break;
    case 'bottom_y':
    val = (this.getCurrentPos('SE').y/this.scale_)/this.img_.getProperty('height');
    break;
  }
  return val;
}

/**
 * Handles mousedown events on the crop handle.
 * @param {Object} e The mousedown event object.
 * @param {String} corner The corner beign activated. e.g. 'NE'.
 * @private
 */
app.db.ImgEditor.prototype.handleCropHandleMouseDown_ = function(e, corner) {
  goog.array.forEach(this.dom.getElementsByTagNameAndClass('div', 'image-editor-crop-handle'), function(val){
    goog.style.setStyle(val,'opacity', 1);
  });
  this.draggers_[corner] = new app.fx.CustomDragger(this.handles_[corner], null, this.getDragLimits_(corner));
  //add the drag event handler
  this.eventHandler_.listen(this.draggers_[corner], goog.fx.Dragger.EventType.DRAG, function(e) {
    this.obj.handleCropHandleDrag_(e,corner);
  }, false, {obj:this,corner:corner});
  //add the dragend event handler
  this.eventHandler_.listen(this.draggers_[corner], goog.fx.Dragger.EventType.END, function(e) {
    this.obj.handleDragEnd_(e, corner);
  }, false, {obj:this,corner:corner});
  this.draggers_[corner].startDrag(e);
}

/**
 * Returns the opposite corner from 'corner'.
 * @param {Object} e The event object.
 * @param {String} corner The corner that was being dragged. e.g. 'NE'.
 * @private
 */
app.db.ImgEditor.prototype.handleDragEnd_ = function(e, corner) {
  goog.array.forEach(this.dom.getElementsByTagNameAndClass('div', 'image-editor-crop-handle'), function(val){
    goog.style.setStyle(val,'opacity', .5);
  });
  this.draggers_[corner].dispose();
}

/**
 * Returns the actual limits of a handle during an adjustment operation.
 * @param {String} corner The corner being dragged, e.g. 'NE'.
 * @private
 */
app.db.ImgEditor.prototype.getDragLimits_ = function(corner) {
  var limits = new goog.math.Rect(0, 0, this.canvasWidth_, this.canvasHeight_);
  switch(corner) {
    case 'NW':
    limits = new goog.math.Rect(0, 0, this.NE_pos.x-20, this.SE_pos.y-20);
    break;
    case 'NE':
    limits = new goog.math.Rect(this.NW_pos.x+20, 0, (this.canvasWidth_-(this.NW_pos.x+20)), this.SE_pos.y-20);
    break;
    case 'SE':
    limits = new goog.math.Rect(this.SW_pos.x+20, this.NE_pos.y+20, (this.canvasWidth_-(this.SW_pos.x+20)), (this.canvasHeight_-(this.NE_pos.y+20)));
    break;
    case 'SW':
    limits = new goog.math.Rect(0, this.NW_pos.y+20, this.SE_pos.x-20, (this.canvasHeight_-(this.NW_pos.y+20)));
    break;
  }
  return limits;
}

/**
 * Handles the drag events.
 * @param {Object} e The drag event.
 * @private
 */
app.db.ImgEditor.prototype.handleCropWindowDrag_ = function(e) {
  this.setCropWindowToRect_(new goog.math.Rect(e.left, e.top, this.cropWindowWidth_, this.cropWindowHeight_));
}

/**
 * Updates the position/size of the crop window in response to dragging.
 * @param {Object} rect The rectangle to set the crop window to.
 * @private
 */
app.db.ImgEditor.prototype.setCropWindowToRect_ = function(rect) {
  this.cropWindowHeight_ = rect.height;
  this.cropWindowWidth_ = rect.width;
  goog.style.setStyle(this.cropWindow_, 'top', rect.top+'px');
  goog.style.setStyle(this.cropWindow_, 'left', rect.left+'px');
  goog.style.setStyle(this.cropWindow_, 'height', rect.height+'px');
  goog.style.setStyle(this.cropWindow_, 'width', rect.width+'px');
  goog.style.setStyle(this.fgImage_, 'top', '-'+rect.top+'px');
  goog.style.setStyle(this.fgImage_, 'left', '-'+rect.left+'px');
  this.updateHandlePos_('NW', new goog.math.Coordinate(rect.left, rect.top));
  this.updateHandlePos_('NE', new goog.math.Coordinate(rect.left+rect.width, rect.top));
  this.updateHandlePos_('SE', new goog.math.Coordinate(rect.left+rect.width, rect.top+rect.height));
  this.updateHandlePos_('SW', new goog.math.Coordinate(rect.left, rect.top+rect.height));
}

/**
 * Returns the opposite corner from 'corner'.
 * @param {String} corner The corner, in the form of 'NE' or 'SW', etc.
 * @private
 */
app.db.ImgEditor.prototype.getCurrentPos = function(corner) {
  return this[corner+'_pos'];
}

/**
 * Returns the opposite corner from 'corner'.
 * @param {String} corner The corner, in the form of 'NE' or 'SW', etc.
 * @private
 */
app.db.ImgEditor.prototype.getOppositeCorner_ = function(corner) {
  var op_corner;
  switch(corner) {
    case 'NW':
      op_corner = this.getCurrentPos('SE');
    break;
    case 'NE':
      op_corner = this.getCurrentPos('SW');
    break;
    case 'SE':
      op_corner = this.getCurrentPos('NW');
    break;
    case 'SW':
      op_corner = this.getCurrentPos('NE');
    break;
  }
  return op_corner;
}

/**
 * Returns the new top left when 'corner' is updated to 'coord'.
 * @param {String} corner The corner, in the form of 'NE' or 'SW', etc.
 * @param {Object} coord The new coordinate of 'corner'.
 * @private
 */
app.db.ImgEditor.prototype.getTopLeftPos_ = function(corner, coord) {
  var x,y = null;
  nw_pos = this.getCurrentPos('NW');
  switch(corner) {
    case 'NW':
      x = coord.x
      y = coord.y
    break;
    case 'NE':
      x = nw_pos.x
      y = coord.y
    break;
    case 'SE':
      x = nw_pos.x;
      y = nw_pos.y;
    break;
    case 'SW':
      x = coord.x;
      y = nw_pos.y;
    break;
  }
  return new goog.math.Coordinate(x,y);
}

/**
 * Returns the new crop window size given two opposite coordinates.
 * @param {Object} coord One of the coordinates.
 * @param {Object} opcoord The opposite coordinate.
 * @private
 */
app.db.ImgEditor.prototype.getNewCropWindowSize_ = function(coord, op_coord) {
  return new goog.math.Size(Math.abs(coord.x - op_coord.x), Math.abs(coord.y - op_coord.y));
}

/**
 * Handles the actual drag events.
 * @param {Object} e The Event Object.
 * @param {String} corner The corner, in the form of 'NE' or 'SW', etc.
 */
app.db.ImgEditor.prototype.handleCropHandleDrag_ = function(e, corner) {
  var left,top,height,width = null;
  var x = e.left;
  var y = e.top;

  // the new position of the dragged corner (before adjustment)
  var new_pos = new goog.math.Coordinate(x,y);
  
  // the position of the opposite corner, used for sizing
  var op_pos = this.getOppositeCorner_(corner);

  // the new size of the crop window (before adjustment)
  var new_size = this.getNewCropWindowSize_(new_pos, op_pos);

  if (this.imgOpts_) {//if we have to stick to some ratio!!!!!!             ############# @@TODO: FIX
    var ratio = new_size.width/new_size.height;
    var too_tall = ratio < parseFloat(this.imgOpts_.min_ratio);
    var too_wide = ratio > parseFloat(this.imgOpts_.max_ratio);
    if (too_tall || too_wide) {
      var diff_from_op = new goog.math.Coordinate.difference(new_pos,op_pos)
      if (too_tall) {
        var offset = Math.abs(diff_from_op.y) * this.imgOpts_.min_ratio;
        x = parseInt((corner == 'NE' || corner == 'SE') ? op_pos.x + offset : op_pos.x - offset);
        
        if(x != e.dragger.limitX(x)) {
          x = e.dragger.limitX(x);
          offset = Math.abs(op_pos.x - x) / this.imgOpts_.min_ratio;
          y = parseInt((corner == 'SW' || corner == 'SE') ? op_pos.y + offset : op_pos.y - offset);
        }
      }
      else{
        var offset = Math.abs(diff_from_op.x)/this.imgOpts_.max_ratio;
        y = parseInt((corner == 'NW' || corner == 'NE') ? op_pos.y - offset : op_pos.y + offset);
        if(y != e.dragger.limitY(y)) {
          y = e.dragger.limitY(y);
          offset = Math.abs(op_pos.y - y) * this.imgOpts_.min_ratio;
          x = parseInt((corner == 'SW' || corner == 'NW') ? op_pos.x - offset : op_pos.x + offset);
        }
      }
      new_pos = new goog.math.Coordinate(x,y);
      new_size = this.getNewCropWindowSize_(new_pos, op_pos);
    }
  }

  var top_left = this.getTopLeftPos_(corner, new_pos);
  this.setCropWindowToRect_(new goog.math.Rect(top_left.x, top_left.y, new_size.width, new_size.height));
  
}

/**
 * Updates a specific handle's position.
 * @param {String} corner The corner, in the format of 'NE'.
 * @param {Object} coord The new coordinates.
 */
app.db.ImgEditor.prototype.updateHandlePos_ = function(corner, coord) {
  this[corner+'_pos'] = coord;
  goog.style.setPosition(this.handles_[corner], coord);
}

/**
 * The ImgEditor events.
 */
app.db.ImgEditor.events = {};

/**
 * The event to signal the end of img editing, either after a crop or without one.
 * @param {app.db.Img} img The final img object.
 * @private
 */
app.db.ImgEditor.events.ImgEditFinished = function(img) {
  goog.events.Event.call(this, 'imgeditfinished');
  this.img_ = img;
};
goog.inherits(app.db.ImgEditor.events.ImgEditFinished, goog.events.Event);

// *** app.db.Img *********************************************** //
/**
 * A wrapper for all db.Model (or subclass) instances on the server.
 * @param {Object} opt_properties The instance properties.
 * @constructor
 */
app.db.Model = function(type, opt_properties) {
  this.type_ = type;
  this.properties_ = opt_properties || {};
  goog.base(this);
}
goog.inherits(app.db.Model, goog.events.EventTarget);
// *** app.db.Img.prototype.getProperty *********************************************** //
/**
 * Returns a property value from the dbModel.
 * @public
 */
app.db.Model.prototype.getProperty = function(prop_name, default_value) {
  res = goog.object.get(this.properties_, prop_name, default_value);
  return res;
}

// *** app.db.Model.prototype.properties_ *********************************************** //
app.db.Model.prototype.properties_ = {};

// *** app.db.Model.prototype.type_ *********************************************** //
app.db.Model.prototype.type_ = {};

// *** app.db.Img *********************************************** //
/**
 * A wrapper for db.Img instances on the server.
 * @param {Object} img_opts The image option variables.
 * @constructor
 */
app.db.Img = function(properties) {
  app.db.Model.call(this, 'Img', properties);
}
goog.inherits(app.db.Img, app.db.Model);

// *** app.db.Img.getId *********************************************** //
/**
 * Get the id
 * @int
 */
app.db.Img.prototype.getId = function() {
  var id = this.getProperty('img_id');
  try {
    id = parseInt(id);
  } catch(e) {
    _logger.log('ERROR: '+e);
  }
  if(id > 0){
    return id;
  }
  throw "bad_image_id";
}

// *** app.db.Img.prototype.buildElement *********************************************** //
/**
 * Returns and img element.
 * @param {Int} size The length of the longest side.
 * @param {Bool} crop Whether or not to crop the image square.
 * @param {Object} opts Further attributes to set on the image element.
 * @public
 */
app.db.Img.prototype.buildElement = function(size, crop, opts) {
  opts = opts || {};
  var src = this.getProperty('url');
  if(size) {
    var src = src + '=s' + size
    if(crop === true) {
      src = src + '-c'
    }
  }
  opts['src'] = src;
  if(goog.object.containsKey(opts, 'class')) {
    opts['class'] = opts['class'] + ' img_id:'+ this.getProperty('img_id');
  }
  else {
    opts['class'] = 'img_id:'+ this.getProperty('img_id');
  }
  opts['src'] = src;
  var elm = goog.dom.createDom('img', opts);
  return elm;
  
}




// *** ImageDialoglugin ***************************************************** //

/**
 * A plugin for the ImageDialog.
 * @constructor
 * @extends {goog.editor.plugins.AbstractDialogPlugin}
 */
app.ui.editor.plugins.ImageDialogPlugin = function() {
  goog.base(this, goog.editor.Command.IMAGE);

};
goog.inherits(app.ui.editor.plugins.ImageDialogPlugin,
              goog.editor.plugins.AbstractDialogPlugin);

/** @inheritDoc */
app.ui.editor.plugins.ImageDialogPlugin.prototype.getTrogClassId =
    goog.functions.constant('ImageDialogPlugin');


// *** Protected interface ************************************************** //


/**
 * Creates a new instance of the dialog and registers for the relevant events.
 * @param {goog.dom.DomHelper} dialogDomHelper The dom helper to be used to
 *     create the dialog.
 * @param {HTMLImageElement} image The source image if exists.
 * @return {app.ui.editor.plugins.ImageDialog} The dialog.
 * @override
 * @protected
 */
app.ui.editor.plugins.ImageDialogPlugin.prototype.createDialog = function(
  dialogDomHelper, image) {
  var dialog = new app.ui.editor.plugins.ImageDialog(dialogDomHelper, image);
  //dialog.buttonSet_ = null;
  dialog.addEventListener(goog.ui.editor.AbstractDialog.EventType.OK,
                          this.handleOk_,
                          false,
                          this);
  return dialog;
};


// *** Private implementation *********************************************** //


/**
 * Handles the OK event from the dialog by inserting the Image
 * into the field.
 * @param {app.ui.editor.plugins.ImageDialog.OkEvent} e OK event object.
 * @private
 */
app.ui.editor.plugins.ImageDialogPlugin.prototype.handleOk_ = function(e) {
  // Notify the editor that we are about to make changes.
  this.fieldObject.dispatchBeforeChange();

  // Grab the url of the image off of the event.
  var image = e.img_.buildElement(
    null, 
    false, 
    {'id':'img_id:'+e.img_.getId(), 'class': 
      'img-display-block', 'style':'margin:15px auto;display:block;'}
  );

  // We want to insert the image in place of the user's selection.
  // So we restore it first, and then use it for insertion.
  this.restoreOriginalSelection();
  var range = this.fieldObject.getRange();
  image = range.replaceContentsWithNode(image);

  // Done making changes, notify the editor.
  this.fieldObject.dispatchChange();

  // Put the user's selection right after the newly inserted image.
  goog.editor.range.placeCursorNextTo(image, false);

  // Dispatch selection change event since we just moved the selection.
  this.fieldObject.dispatchSelectionChangeEvent();
};


//**  ImageDialog *********************************************************** //
//**  ImageDialog *********************************************************** //
//**  ImageDialog *********************************************************** //

/**
 * A dialog for editing/uploading an image.
 * @param {goog.dom.DomHelper} domHelper DomHelper to be used to create the
 *     dialog's DOM structure.
 * @param {HTMLImageElement} image The image.
 * @constructor
 * @extends {goog.ui.editor.AbstractDialog}
 */
app.ui.editor.plugins.ImageDialog = function(opt_domHelper, img) {
  goog.base(this, opt_domHelper);
  this.img_ = img;

  /**
   * The event handler for this dialog.
   * @type {goog.events.EventHandler}
   * @private
   */
  this.eventHandler_ = new goog.events.EventHandler(this);
};
goog.inherits(app.ui.editor.plugins.ImageDialog, goog.ui.editor.AbstractDialog);

//************** {Object} app.db.ImgSelector.prototype.img_ **************************************/
/**
 * The selected img, if any.
 * @type {HTMLImageElement}
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.img_;

//************** {Object} app.db.ImgSelector.prototype.dialogControl_ **************************************/
/**
 * The dialog control
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.dialogControl_;

//************** {Object} app.db.ImgSelector.prototype.progressAnimation_ **************************************/
/**
 * The Progress Animation.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.progressAnimation_ = null;

// *** Event **************************************************************** //

/**
 * OK event object for the image dialog.
 * @param {string} imageUrl Url the image.
 * @constructor
 * @extends {goog.events.Event}
 */
app.ui.editor.plugins.ImageDialog.OkEvent = function(img) {
  goog.base(this, goog.ui.editor.AbstractDialog.EventType.OK);

  /**
   * The url of the image edited in the dialog.
   * @type {string}
   */
  this.img_ = img;
};
goog.inherits(app.ui.editor.plugins.ImageDialog.OkEvent, goog.events.Event);


/** @inheritDoc */
app.ui.editor.plugins.ImageDialog.prototype.show = function() {
  goog.base(this, 'show');
};


// *** createDialogControl ************************************************** //

/** @inheritDoc */
app.ui.editor.plugins.ImageDialog.prototype.createDialogControl = function(img) {
  this.img_ = img;
  this.builder_ = new goog.ui.editor.AbstractDialog.Builder(this);
  this.builder_.addOkButton();
  this.dialogControl_ = this.builder_.build();
  this.dialogControl_.getButtonSet().setButtonEnabled(
    goog.ui.Dialog.DefaultButtonKeys.OK, false);
  
  if(!this.img_) {
    this.loadSelector_();
  } else {
    this.loadEditor_(this.img_);
  }
  return this.dialogControl_;
};
/**
 * Reposition the dialog.
 * @public
 */
app.ui.editor.plugins.ImageDialog.prototype.reposition = function() {
  this.dialogControl_.reposition();
}
/**
 * Update the content.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.updateContent = function(content) {
  goog.dom.removeChildren(this.dialogControl_.contentEl_);
  goog.dom.appendChild(this.dialogControl_.contentEl_, content);
}
/**
 * Update the Title
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.updateTitle = function(title) {
  this.dialogControl_.setTitle(title);
}
/**
 * The goog.ui.editor.AbstractDialog.Builder object
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.builder_ = null;

/**
 * The app.db.ImgSelector object
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.imgSelector_ = null;

/**
 * The app.db.ImgSelector object
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.imgEditor_ = null;


/**
 * Loads the imgSelector_ in the dialog, creating/flushing as necessary.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.loadSelector_ = function() {
  if (!this.imgSelector_) {
    this.imgSelector_ = new app.db.ImgSelector(this.dom);
  }
  var content = this.dom.createDom(goog.dom.TagName.DIV, null);
  //goog.dom.appendChild(content, this.imgSelector_.buildFetchImageElement_());
  goog.dom.appendChild(content, this.imgSelector_.buildUploadImageElement_());
  this.updateTitle('Upload Or Fetch An Image');
  this.updateContent(content);
  this.eventHandler_.listen(this.imgSelector_, 'imgselected', this.onImgSelected_);
  this.eventHandler_.listen(this.imgSelector_, 'startloading', this.onStartLoading_);
  this.eventHandler_.listen(this.imgSelector_, 'endloading', this.onEndLoading_);
  this.reposition();
};

/**
 * Loads the imgEditor_ in the dialog, creating/flushing as necessary.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.loadEditor_ = function(img) {
  var img_to_edit = img || this.img_;
  if (!this.imgEditor_) {
    this.imgEditor_ = new app.db.ImgEditor(this.dom);
  }
  var content = this.imgEditor_.buildEditor(img_to_edit);
  this.updateTitle('Edit The Image');
  this.updateContent(content);
  this.eventHandler_.listen(this.imgEditor_, 'imgeditfinished', this.onImgEditFinished_);
  this.eventHandler_.listen(this.imgEditor_, 'startloading', this.onStartLoading_);
  this.eventHandler_.listen(this.imgEditor_, 'endloading', this.onEndLoading_);
  this.setupEditorButtons();
  this.reposition();
};
/**
 * Sets up the buttons needed for the editor.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.setupEditorButtons = function() {
  this.dialogControl_.setButtonSet(app.ui.editor.plugins.ImageDialog.
    createAcceptOrCropButtonSet(goog.dom.getDomHelper(this)));
  this.eventHandler_.listen(this.dialogControl_, goog.ui.Dialog.EventType.SELECT, function(e) {
    switch(e.key) {
      case 'crop':
        this.imgEditor_.triggerCrop_(e);
      break;
      case 'accept':
        this.imgEditor_.triggerEditFinish_();
      break;
    }
  });
  
}

/**
 * Creates a new ButtonSet with 'Finish' and 'Crop and Finish' buttons.
 * @return {!goog.ui.Dialog.ButtonSet} The created ButtonSet.
 */
app.ui.editor.plugins.ImageDialog.createAcceptOrCropButtonSet = function(opt_domhelper) {
  return new goog.ui.Dialog.ButtonSet(opt_domhelper).
    addButton({key: 'crop', caption: 'Crop and Accept Image'}).
    addButton({key: 'accept', caption: 'Accept Without Cropping'});
};
/**
 * The ImageDialog method to trigger a FINISH action on the internal ImgEditor object.
 */
app.ui.editor.plugins.ImageDialog.prototype.triggerImgEditorFinish_ = function(e) {
  e.preventDefault();
  if(this.imgEditor_) {
    this.imgEditor_.triggerEditFinish_();
  }
}

/**
 * The ImageDialog method to trigger a crop action on the internal ImgEditor object.
 */
app.ui.editor.plugins.ImageDialog.prototype.triggerImgEditorCrop_ = function(e) {
  e.preventDefault();
  if(this.imgEditor_ != null) {
    this.imgEditor_.triggerCrop_();
  }
}

/**
 * Handles the app.events.startLoadingEvent.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.onStartLoading_ = function(e) {
  if (this.progressAnimation_) {
    this.progressAnimation_.dispose();
  }
  this.progressAnimation_ = new app.ui.ProgressAnimation(e.msg_);
  this.updateContent(this.progressAnimation_.getElement());
  this.progressAnimation_.startAnimation();
};

/**
 * Handles the app.db.ImgSelector.onEndLoading_ Event.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.onEndLoading_ = function(e) {
};

/**
 * Handles the app.db.ImgSelector.imgSelectedEvent Event.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.onImgSelected_ = function(e) {
  this.img_ = e.selectedImg_;
  this.loadEditor_(this.img_);
};

/**
 * Handles the app.db.ImgSelector.imgSelectedEvent Event.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.onImgEditFinished_ = function(e) {
  this.triggerImgReady(e.img_);
};

/**
 * Handles imgReadyEvent.
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.triggerImgReady = function(img) {
  this.dispatchEvent(new app.ui.editor.plugins.ImageDialog.OkEvent(img || this.img_));
  this.disposeInternal();
};

/** @inheritDoc */
app.ui.editor.plugins.ImageDialog.prototype.disposeInternal = function() {
  this.eventHandler_.dispose();
  this.eventHandler_ = null;
  goog.base(this, 'disposeInternal');
};

/**
 * EventHandler object that keeps track of all handlers set by this dialog.
 * @type {goog.events.EventHandler}
 * @private
 */
app.ui.editor.plugins.ImageDialog.prototype.eventHandler_;

/** @inheritDoc */
app.ui.editor.plugins.ImageDialog.prototype.disposeInternal = function() {
  goog.base(this, 'disposeInternal');
};

/**
 * The event that closes the dialog and hands back to the ImageDialogPlugin.
 * @type {goog.events.EventHandler}
 * @private
 */
app.ui.editor.plugins.ImageDialog.OkEvent = function(img) {
  goog.base(this, goog.ui.editor.AbstractDialog.EventType.OK);
  this.img_ = img;
}
goog.inherits(app.ui.editor.plugins.ImageDialog.OkEvent, goog.events.Event);



// *** app.ui.editor.plugins.CodeDialogPlugin ***************************************************** //
/**
 * A plugin for the CodeDialog.
 * @constructor
 * @extends {goog.editor.plugins.AbstractDialogPlugin}
 */
app.ui.editor.plugins.CodeDialogPlugin = function() {
  goog.base(this, 'code');
};
goog.inherits(app.ui.editor.plugins.CodeDialogPlugin, goog.editor.plugins.AbstractDialogPlugin);

/** @inheritDoc */
app.ui.editor.plugins.CodeDialogPlugin.prototype.getTrogClassId = goog.functions.constant('CodeDialogPlugin');

/**
 * Creates a new instance of the dialog and registers for the relevant events.
 * @param {goog.dom.DomHelper} dialogDomHelper The dom helper to be used to
 *     create the dialog.
 * @param {HTMLImageElement} image The source image if exists.
 * @return {app.ui.editor.plugins.ImageDialog} The dialog.
 * @override
 * @protected
 */
app.ui.editor.plugins.CodeDialogPlugin.prototype.createDialog = function(dialogDomHelper, code) {
  var dialog = new app.ui.editor.plugins.CodeDialog(dialogDomHelper, code);
  dialog.addEventListener(goog.ui.editor.AbstractDialog.EventType.OK, this.handleOk_, false, this);
 
  return dialog;
};

/**
 * Handles the OK event from the dialog by inserting the Image
 * into the field.
 * @param {app.ui.editor.plugins.ImageDialog.OkEvent} e OK event object.
 * @private
 */
app.ui.editor.plugins.CodeDialogPlugin.prototype.handleOk_ = function(e) {
  // Notify the editor that we are about to make changes.
  this.fieldObject.dispatchBeforeChange();

  // We want to insert the image in place of the user's selection.
  // So we restore it first, and then use it for insertion.
  this.restoreOriginalSelection();
  var range = this.fieldObject.getRange();
  image = range.replaceContentsWithNode(e.codeElem_);

  // Done making changes, notify the editor.
  this.fieldObject.dispatchChange();

  // Put the user's selection right after the newly inserted image.
  goog.editor.range.placeCursorNextTo(e.codeElem_, false);

  // Dispatch selection change event since we just moved the selection.
  this.fieldObject.dispatchSelectionChangeEvent();
};

//************** {Object} app.ui.editor.plugins.CodeDialog **************************************/
/**
 * A dialog inserting a block of code.
 * @param {goog.dom.DomHelper} domHelper DomHelper to be used to create the
 *     dialog's DOM structure.
 * @param {HTMLImageElement} image The image.
 * @constructor
 * @extends {goog.ui.editor.AbstractDialog}
 */
app.ui.editor.plugins.CodeDialog = function(opt_domHelper, code) {
  goog.base(this, opt_domHelper);
  this.codeElem_ = code;

  /**
   * The event handler for this dialog.
   * @type {goog.events.EventHandler}
   * @private
   */
  this.eventHandler_ = new goog.events.EventHandler(this);
};
goog.inherits(app.ui.editor.plugins.CodeDialog, goog.ui.editor.AbstractDialog);

app.ui.editor.plugins.CodeDialog.prototype.codeSnippet_ = null;
app.ui.editor.plugins.CodeDialog.prototype.codeElem_ = null;
app.ui.editor.plugins.CodeDialog.prototype.lang_ = null;

// *** createDialogControl ************************************************** //

/** @inheritDoc */
app.ui.editor.plugins.CodeDialog.prototype.createDialogControl = function() {
  if(this.codeElem_) {
    this.codeSnippet_ = goog.dom.getDomHelper(this.codeElem_).getTextContent();
    this.lang_ = this.codeElem_.lang;
  }
  var builder = new goog.ui.editor.AbstractDialog.Builder(this);
  builder.setTitle('Insert A Code Snippet');
  var dom = goog.dom.getDomHelper(this);
  var content = dom.createDom('div');
  this.snippetTextArea_ = dom.createDom('TEXTAREA', {style:'width:98%;min-height:300px;'}, this.codeSnippet_ || '');
  this.langSelectInput_ = dom.createDom('SELECT', null);
  goog.dom.appendChild(this.langSelectInput_, dom.createDom('OPTION', {value: 'python', selected: (this.lang_ == 'python') ? 'selected' : ''}, 'Python'));
  goog.dom.appendChild(this.langSelectInput_, dom.createDom('OPTION', {value: 'javascript', selected: (this.lang_ == 'javascript') ? 'selected' : ''}, 'Javascript'));
  goog.dom.appendChild(this.langSelectInput_, dom.createDom('OPTION', {value: 'java', selected: (this.lang_ == 'java') ? 'selected' : ''}, 'Java'));
  var langDiv_ = dom.createDom('DIV', {style: 'margin-bottom:10px;'}, dom.createDom('h3', {}, dom.createDom('span', {}, 'Langauge')));
  var snippetDiv_ = dom.createDom('DIV', null, dom.createDom('h3', {}, dom.createDom('span', {}, 'Snippet')));
  goog.dom.appendChild(langDiv_, this.langSelectInput_);
  goog.dom.appendChild(snippetDiv_, this.snippetTextArea_);
  goog.dom.appendChild(content, langDiv_);
  goog.dom.appendChild(content, snippetDiv_);
  var control_ = builder.build();
  goog.dom.removeChildren(control_.contentEl_);
  goog.dom.appendChild(control_.contentEl_, content);
  return control_;
};

/**
 * Creates and returns the event object to be used when dispatching the OK
 * event to listeners based on which tab is currently selected and the contents
 * of the input fields of that tab.
 * @return {goog.editor.plugins.ImageDialog.OkEvent} The event object to be used when
 *     dispatching the OK event to listeners.
 * @protected
 * @override
 */
app.ui.editor.plugins.CodeDialog.prototype.createOkEvent = function() {
  var lang_ = this.langSelectInput_.value;
  var snippet_ = this.snippetTextArea_.value;
  if (lang_ && snippet_) {
    var ev = new app.ui.editor.plugins.CodeDialog.OkEvent(goog.dom.createDom('pre', {lang: lang_, style: 'background-color:#ffc;'}, snippet_));
    return ev;
  } else {
    _logger.log('Language not selected or no code input.');
  }
};

/** @inheritDoc */
app.ui.editor.plugins.CodeDialog.prototype.disposeInternal = function() {
  goog.base(this, 'disposeInternal');
};

/**
 * OK event object for the image dialog.
 * @param {string} imageUrl Url the image.
 * @constructor
 * @extends {goog.events.Event}
 */
app.ui.editor.plugins.CodeDialog.OkEvent = function(code_elem) {
  goog.base(this, goog.ui.editor.AbstractDialog.EventType.OK);
  this.codeElem_ = code_elem;
};
goog.inherits(app.ui.editor.plugins.CodeDialog.OkEvent, goog.events.Event);

app.ui.editor.plugins.CodeDialog.OkEvent.prototype.codeElem_ = null;

// Copyright 2010 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.



/**
 * Property bubble plugin for image.
 * @constructor
 * @extends {goog.editor.plugins.AbstractBubblePlugin}
 */
app.ui.editor.plugins.ImageBubble = function() {
  goog.base(this);
};
goog.inherits(app.ui.editor.plugins.ImageBubble,
    goog.editor.plugins.AbstractBubblePlugin);


/**
 * Element id for the change image span.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.CHANGE_IMAGE_SPAN_ID_ = 'tr_change-image-span';

/**
 * Element id for the display block span.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.DISPLAY_BLOCK_ID_ = 'tr_display-block-span';

/**
 * Element id for the float left span.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.FLOAT_LEFT_ID_ = 'tr_float-left-span';

/**
 * Element id for the float left span.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.FLOAT_RIGHT_ID_ = 'tr_float-right-span';

/**
 * Element id for the image.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.CHANGE_IMAGE_ID_ = 'tr_change-image';

/**
 * Element id for the delete image.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.DELETE_IMAGE_ID_ = 'tr_delete-image';


/**
 * Element id for the image bubble wrapper div.
 * type {string}
 * @private
 */
app.ui.editor.plugins.ImageBubble.IMAGE_DIV_ID_ = 'tr_image-div';


/**
 * @desc Label that pops up a bubble caption.
 */
var MSG_IMAGE_BUBBLE = goog.getMsg('Add an image');


/**
 * @desc Label of edit the image action.
 */
var MSG_IMAGE_BUBBLE_CHANGE = goog.getMsg('Edit');

/**
 * @desc Label of float image left action.
 */
var MSG_IMAGE_BUBBLE_FLOAT_LEFT = goog.getMsg('Float Left');

/**
 * @desc Label of float image right action.
 */
var MSG_IMAGE_BUBBLE_FLOAT_RIGHT = goog.getMsg('Float Right');

/**
 * @desc Label of display image block action.
 */
var MSG_IMAGE_BUBBLE_DISPLAY_BLOCK = goog.getMsg('Display Block');

/**
 * @desc Label of remove this image action.
 */
var MSG_IMAGE_BUBBLE_REMOVE = goog.getMsg('Remove');


/** @inheritDoc */
app.ui.editor.plugins.ImageBubble.prototype.getTrogClassId = function() {
  return 'ImageBubble';
};

/**
 * @type {string}
 */
app.ui.editor.plugins.ImageBubble.CLASS_NAME = 'ImageBubbleClass';


/** @inheritDoc */
app.ui.editor.plugins.ImageBubble.prototype.getBubbleTargetFromSelection =
    function(selectedElement) {
  var bubbleTarget = goog.dom.getAncestorByTagNameAndClass(selectedElement,
      goog.dom.TagName.IMG);

  if (!bubbleTarget) {
    // See if the selection is touching the right side of a link, and if so,
    // show a bubble for that link.  The check for "touching" is very brittle,
    // and currently only guarantees that it will pop up a bubble at the
    // position the cursor is placed at after the link dialog is closed.
    // NOTE(robbyw): This assumes this method is always called with
    // selected element = range.getContainerElement().  Right now this is true,
    // but attempts to re-use this method for other purposes could cause issues.
    // TODO(robbyw): Refactor this method to also take a range, and use that.
    var range = this.fieldObject.getRange();
    if (range && range.isCollapsed() && range.getStartOffset() == 0) {
      var startNode = range.getStartNode();
      var previous = startNode.previousSibling;
      if (previous && previous.tagName == goog.dom.TagName.IMG) {
        bubbleTarget = previous;
      }
    }
  }

  return /** @type {Element} */ (bubbleTarget);
};


/** @inheritDoc */
app.ui.editor.plugins.ImageBubble.prototype.getBubbleType = function() {
  return goog.dom.TagName.IMG;
};


/** @inheritDoc */
app.ui.editor.plugins.ImageBubble.prototype.getBubbleTitle = function() {
  return MSG_IMAGE_BUBBLE;
};


/** @inheritDoc */
app.ui.editor.plugins.ImageBubble.prototype.createBubbleContents = function(
    bubbleContainer) {

  var changeImageSpan = this.dom_.createDom(goog.dom.TagName.SPAN,
      { id: app.ui.editor.plugins.ImageBubble.CHANGE_IMAGE_SPAN_ID_,
        className: goog.editor.plugins.AbstractBubblePlugin.OPTION_LINK_CLASSNAME_});

  this.createLink(app.ui.editor.plugins.ImageBubble.CHANGE_IMAGE_ID_,
      MSG_IMAGE_BUBBLE_CHANGE, this.showImageDialog_, changeImageSpan);

  var removeImageSpan = this.createLinkOption(
      app.ui.editor.plugins.ImageBubble.DELETE_IMAGE_SPAN_ID_);

  this.createLink(app.ui.editor.plugins.ImageBubble.DELETE_IMAGE_ID_,
      MSG_IMAGE_BUBBLE_REMOVE, this.deleteImage_, removeImageSpan);

  var floatLeftSpan = this.createLinkOption(
      app.ui.editor.plugins.ImageBubble.FLOAT_LEFT_SPAN_ID_);
  var floatRightSpan = this.createLinkOption(
      app.ui.editor.plugins.ImageBubble.FLOAT_RIGHT_SPAN_ID_);

  var displayBlockSpan = this.createLinkOption(
      app.ui.editor.plugins.ImageBubble.DISPLAY_BLOCK_SPAN_ID_);



  this.createLink(app.ui.editor.plugins.ImageBubble.FLOAT_LEFT_ID_,
      MSG_IMAGE_BUBBLE_FLOAT_LEFT, this.floatImageLeft_, floatLeftSpan);
  this.createLink(app.ui.editor.plugins.ImageBubble.FLOAT_RIGHT_ID_,
      MSG_IMAGE_BUBBLE_FLOAT_RIGHT, this.floatImageRight_, floatRightSpan);

  this.createLink(app.ui.editor.plugins.ImageBubble.DISPLAY_BLOCK_ID_,
      MSG_IMAGE_BUBBLE_DISPLAY_BLOCK, this.displayImageBlock_, displayBlockSpan);


  this.onShow();

  var bubbleContents = this.dom_.createDom(goog.dom.TagName.DIV,
    {id: app.ui.editor.plugins.ImageBubble.IMAGE_DIV_ID_}, removeImageSpan, floatLeftSpan, displayBlockSpan, floatRightSpan);

  goog.dom.appendChild(bubbleContainer, bubbleContents);
};


/**
 * Gets the text to display for a image, based on the type of image
 * @return {Object} Returns an object of the form:
 *     {imageSrc: displayTextForImageSrc, imageAlt: displayTextForImageAlt}.
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.getImageToTextObj_ = function() {
  var alt = this.getTargetElement().getAttribute('alt') || '';
  var src = this.getTargetElement().getAttribute('src') || '';

  return {imageSrc: src, imageAlt: alt};
};


/**
 * Float the image left.
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.floatImageLeft_ = function() {
  this.fieldObject.dispatchBeforeChange();
  var elm_ = this.getTargetElement();
  goog.style.setStyle(elm_, 'cssFloat', 'left');
  goog.style.setStyle(elm_, 'marginLeft', '0');
  goog.style.setStyle(elm_, 'marginRight', '10px');
  goog.dom.classes.remove(elm_, 'img-float-right');
  goog.dom.classes.remove(elm_, 'img-display-block');
  goog.dom.classes.add(elm_, 'img-float-left');
  this.closeBubble();
  this.fieldObject.dispatchChange();
};

/**
 * Float the image right.
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.floatImageRight_ = function() {
  this.fieldObject.dispatchBeforeChange();
  var elm_ = this.getTargetElement();
  goog.style.setStyle(elm_, 'cssFloat', 'right');
  goog.style.setStyle(elm_, 'marginRight', '0');
  goog.style.setStyle(elm_, 'marginLeft', '10px');
  goog.dom.classes.remove(elm_, 'img-display-block');
  goog.dom.classes.remove(elm_, 'img-float-left');
  goog.dom.classes.add(elm_, 'img-float-right');
  this.closeBubble();
  this.fieldObject.dispatchChange();
};

/**
 * Display the image 'block' style.
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.displayImageBlock_ = function() {
  this.fieldObject.dispatchBeforeChange();
  var elm_ = this.getTargetElement();
  goog.style.setStyle(elm_, 'display', 'block');
  goog.dom.classes.remove(elm_, 'img-float-left');
  goog.dom.classes.remove(elm_, 'img-float-right');
  goog.dom.classes.add(elm_, 'img-display-block');
  goog.style.setStyle(elm_, 'cssFloat', 'none');
  goog.style.setStyle(elm_, 'clear', 'both');
  this.closeBubble();
  this.fieldObject.dispatchChange();
};

/**
 * Deletes the image associated with the bubble
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.deleteImage_ = function() {
  this.fieldObject.dispatchBeforeChange();
  goog.dom.removeNode(this.getTargetElement());
  this.closeBubble();
  this.fieldObject.dispatchChange();
};


/**
 * Shows the image dialog
 * @private
 */
app.ui.editor.plugins.ImageBubble.prototype.showImageDialog_ = function() {
  this.fieldObject.execCommand(goog.editor.Command.IMAGE, this.getTargetElement());
  this.closeBubble();
};

app.ui.editor.plugins.HeaderFormatter = function() {
}
goog.inherits(app.ui.editor.plugins.HeaderFormatter, goog.editor.plugins.HeaderFormatter);

/**
 * Commands that can be passed as the optional argument to execCommand.
 * @enum {string}
 */
app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND = {
  H2: 'H2',
  H3: 'H3',
  H4: 'H4'
};

/**
 * @inheritDoc
 */
app.ui.editor.plugins.HeaderFormatter.prototype.handleKeyboardShortcut = function(
    e, key, isModifierPressed) {
  if (!isModifierPressed) {
    return false;
  }
  var command = null;
  switch (key) {
    case '1':
      //command = app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND.H1;
      break;
    case '2':
      command = app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND.H2;
      break;
    case '3':
      command = app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND.H3;
      break;
    case '4':
      command = app.ui.editor.plugins.HeaderFormatter.HEADER_COMMAND.H4;
      break;
  }
  if (command) {
    this.fieldObject.execCommand(
        goog.editor.Command.FORMAT_BLOCK, command);
    // Prevent default isn't enough to cancel tab navigation in FF.
    if (goog.userAgent.GECKO) {
      e.stopPropagation();
    }
    return true;
  }
  return false;
};


//register that the script has been parsed
_onloadKickOff('script');
_logger.log("Finished loading main.js");
