/*global window, document, jQuery, Handsontable, NVMetadata */
(function ($) {
  'use strict';

  /*jslint unparam: true */
  var boldRenderer = function (instance, td, row, col, prop,
    value, cellProperties) {
    //jshint unused:false

    Handsontable.renderers.TextRenderer.apply(this, arguments);
    td.style.fontWeight = 'bold';
  };

  $(document).ready(function () {
    var container = document.getElementById('hot'),
      hot = new Handsontable(container, {
        data: window.NVMetadata.data,
        stretchH: 'all',
        colHeaders: true,
        rowHeaders: true,
        contextMenu: true,
        height: 400,
        cells: function (r) {
          if (r === 0) {
            this.renderer = boldRenderer;
          }
        }
      });

    $('.btn-save-metadata').click(function () {
      $.ajax({
        type: 'POST',
        data: JSON.stringify(hot.getData()),
        contentType: 'application/json; charset=utf-8'
      })
        .done(function () {
          var collectionId = NVMetadata.getCollectionIdFromURL(
            window.location.href
          );
          window.location.replace('/collections/' + collectionId);
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
          NVMetadata.displayErrors($('.errors'),
            NVMetadata.getErrors(jqXHR, textStatus, errorThrown));
        });
    });

    window.onbeforeunload = function () {
      if (window.sheetModified) {
        return 'You have pending unsaved changes. ' +
          'Do you really want to discard them ?';
      }
    };
  });

}(jQuery));
