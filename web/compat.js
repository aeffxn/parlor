/* Small fallbacks for older mobile Safari (including iOS 9). */
(function () {
  'use strict';
  var root = document.documentElement;
  var probe = document.createElement('div').style;
  probe.display = 'grid';
  if (probe.display !== 'grid') root.className += ' no-grid';

  if (!Object.assign) {
    Object.assign = function (target) {
      if (target == null) throw new TypeError('Cannot convert undefined or null to object');
      var output = Object(target);
      for (var i = 1; i < arguments.length; i += 1) {
        var source = arguments[i];
        if (source != null) {
          for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key)) output[key] = source[key];
          }
        }
      }
      return output;
    };
  }

  if (window.Promise && !Promise.prototype.finally) {
    Promise.prototype.finally = function (callback) {
      var PromiseType = this.constructor;
      return this.then(function (value) {
        return PromiseType.resolve(callback()).then(function () { return value; });
      }, function (reason) {
        return PromiseType.resolve(callback()).then(function () { throw reason; });
      });
    };
  }

  if (window.NodeList && !NodeList.prototype.forEach) {
    NodeList.prototype.forEach = Array.prototype.forEach;
  }
  if (window.HTMLCollection && !HTMLCollection.prototype.forEach) {
    HTMLCollection.prototype.forEach = Array.prototype.forEach;
  }
  if (window.Element && !Element.prototype.remove) {
    Element.prototype.remove = function () {
      if (this.parentNode) this.parentNode.removeChild(this);
    };
  }

  if (!window.fetch && window.XMLHttpRequest && window.Promise) {
    window.fetch = function (url, options) {
      options = options || {};
      return new Promise(function (resolve, reject) {
        var request = new XMLHttpRequest();
        request.open(options.method || 'GET', url, true);
        if (options.headers) {
          for (var name in options.headers) {
            if (Object.prototype.hasOwnProperty.call(options.headers, name)) {
              request.setRequestHeader(name, options.headers[name]);
            }
          }
        }
        request.onreadystatechange = function () {
          if (request.readyState !== 4) return;
          resolve({
            status: request.status,
            ok: request.status >= 200 && request.status < 300,
            json: function () {
              return new Promise(function (accept, fail) {
                try { accept(JSON.parse(request.responseText)); }
                catch (error) { fail(error); }
              });
            }
          });
        };
        request.onerror = function () { reject(new Error('Network request failed')); };
        request.ontimeout = function () { reject(new Error('Network request timed out')); };
        request.send(options.body || null);
      });
    };
  }
})();
