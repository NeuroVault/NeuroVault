/*global window */
(function () {
  'use strict';

  window.NVMetadata = window.NVMetadata || {};
  var NVMetadata = window.NVMetadata;

  NVMetadata.getCollectionIdFromURL = function (url) {
    var match = url.match(/collections\/(\d+)/);
    if (match[1]) {
      return match[1];
    }
    return '';
  };

  /*jslint unparam: true */
  NVMetadata.getErrors = function (jqXHR, textStatus, errorThrown) {
    var r = jqXHR.responseJSON,
      errors;

    if (r) {
      errors = [{
        msg: r.message
      }];
    } else {
      errors = [{
        msg: 'Error while submitting data to server: ' + errorThrown
      }];
    }

    return errors;
  };

  NVMetadata.displayErrors = function ($el, errors) {
    var len = errors.length,
      i;

    $el.empty();

    for (i = 0; i < len; i += 1) {
      $el.append('<div>' + errors[i].msg + '</div>');
    }
    $el.show();
  };
}());
