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

  function genAutocompleteRenderer(fieldName) {
    return function (instance, td, row, col, prop,
      value, cellProperties) {

      Handsontable.renderers.AutocompleteRenderer.apply(this, arguments);
      cellProperties.source = getSource(fieldName);
      cellProperties.editor = Handsontable.editors.DropdownEditor;
    };
  }

  function headerNames(headers) {
    return headers.map(function(x) {
      if (x.required) {
        return x.name + '*';
      }
      return x.name;
    });
  }

  function guessFieldType(field) {
    if (field.datasource) {
      return 'autocomplete';
    } else {
      return 'text';
    }
  }

  function getDataSource(field) {
    var datasource = field.datasource;

    if (datasource) {
      if (datasource.choices) {
        return NVMetadata.datasources[datasource.choices];
      }
      else if (datasource.url) {
        return cachedAjaxSource(datasource.url);
      }
    } else {
      return undefined;
    }
  }

  function stringRequiredValidator (value, callback) {
    if (value && /\S/.test(value)) {
      return callback(true);
    } else {
      return callback(false);
    }
  }

  function getFieldValidator(field) {
    if (field.required && !field.datasource) {
      return stringRequiredValidator;
    } else {
      return undefined;
    }
  }

  function columnSettings(headers) {
    return headers.map(function(x) {
      return {
        type: guessFieldType(x),
        source: getDataSource(x),
        strict: x.required,
        validator: getFieldValidator(x)
      }
    });
  }

  function getDefaultHeight(data) {
    var minHeight = 400,
      rowHeight = 24;

    if ((data.length + 1) * rowHeight < minHeight) {
      return minHeight;
    } else {
      return undefined;
    }
  }

  $(document).ready(function () {

    var container = document.getElementById('hot'),
      hot = new Handsontable(container, {
        data: window.NVMetadata.data,
        stretchH: 'all',
        colHeaders: headerNames(window.NVMetadata.dataHeaders),
        columns: columnSettings(window.NVMetadata.dataHeaders),
        rowHeaders: true,
        contextMenu: true,
        height: getDefaultHeight(window.NVMetadata.data),
        cells: function (r, c, prop) {
          if (c === 0) {
            return {readOnly: true};
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
