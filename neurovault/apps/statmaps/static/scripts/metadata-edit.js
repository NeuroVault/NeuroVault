/*global window, document, jQuery, Handsontable, NVMetadata */
(function ($) {
  'use strict';

  function isString(val) {
    return (typeof val === 'string' || val instanceof String);
  }

  function hasChoices(fieldName) {
    return NVMetadata.datasources
      && (NVMetadata.datasources[fieldName] !== undefined);
  }

  function cache() {
    var storage = {};
    return {
      get: function(key) {
        return storage[key];
      },
      set: function(key, value) {
        storage[key] = value;
      }
    }
  }

  var cache = cache();

  function cachedAjaxSource(source) {
    return function (query, process) {
      var data = cache.get(source);
      if (data) {
        process(data);
      } else {
        $.ajax({
          url: source,
          dataType: 'json',
          success: function (response) {
            cache.set(source, response.data);
            process(response.data);
          }
        });
      }
    }
  }

  function getSource(fieldName) {
    var source = NVMetadata.datasources[fieldName];

    if(isString(source)) {
      return cachedAjaxSource(source);
    }
    else {
      return NVMetadata.datasources[fieldName];
    }
  }

  var boldRenderer = function (instance, td, row, col, prop,
    value, cellProperties) {

    Handsontable.renderers.TextRenderer.apply(this, arguments);
    td.style.fontWeight = 'bold';
  };

  function genAutocompleteRenderer(fieldName) {
    return function (instance, td, row, col, prop,
      value, cellProperties) {

      Handsontable.renderers.AutocompleteRenderer.apply(this, arguments);
      cellProperties.source = getSource(fieldName);
      cellProperties.editor = Handsontable.editors.DropdownEditor;
    };
  }

  $(document).ready(function () {

    var container = document.getElementById('hot'),
      hot = new Handsontable(container, {
        data: window.NVMetadata.data,
        stretchH: 'all',
        colHeaders: true,
        rowHeaders: true,
        contextMenu: true,
        height: 400,
        cells: function (r, c, prop) {
          if (r === 0) {
            this.renderer = boldRenderer;
          }
          if (c === 0) {
            return {readOnly: true};
          }

          if (r !== 0) {
            var fieldName = this.instance.getDataAtCell(0, c);
            if (hasChoices(fieldName)) {
              this.renderer = genAutocompleteRenderer(fieldName);
            }
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
