/*global window, document, jQuery, Handsontable, NVMetadata */
(function ($) {
  'use strict';

  function isString(val) {
    return (typeof val === 'string' || val instanceof String);
  }

  function hasChoices(fieldName) {
    return NVMetadata.datasources && (NVMetadata.datasources[fieldName] !== undefined);
  }

  function cache() {
    var storage = {};
    return {
      get: function (key) {
        return storage[key];
      },
      set: function (key, value) {
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

    if (isString(source)) {
      return cachedAjaxSource(source);
    } else {
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
    return headers.map(function (x) {
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
      } else if (datasource.url) {
        return cachedAjaxSource(datasource.url);
      }
    } else {
      return undefined;
    }
  }

  function notEmptyOrSpaced(value) {
    return value && /\S/.test(value)
  }

  function stringRequiredValidator(value, callback) {
    if (notEmptyOrSpaced(value)) {
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
    return headers.map(function (x) {
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

  function columnExist(columnName) {
    var value = columnName.trim(),
      elems = NVMetadata.headers.filter(function(x) {
        return x.name === value;
      });

    return elems.length !== 0;
  }

  function serializeTable(hotInstance) {
    return [window.NVMetadata.headers.map(function (x) {
      return x.name
    })].concat(hotInstance.getData());
  }

  function validateInput(value, success, failure) {
    if (!notEmptyOrSpaced(value)) {
      failure();
    }
    else if (columnExist(value)) {
      failure("Column already exists");
    }
    else {
      success();
    }
  }

  function showError($el, msg) {
    $el.addClass('has-error');
    if (msg) {
      $('.help-block', $el).text(msg);
    }
  }

  function clearError($el) {
    $('.help-block', $el).empty();
    $el.removeClass('has-error');
  }

  function getNewColumnName(callback) {
    var $modalEl = $('#columnNameModal'),
      $submit = $('button[type="submit"]', $modalEl),
      $columnNameEl = $('#column-name'),
      $inputWrapper = $('.js-input-wrapper', $modalEl);

    $modalEl.on('shown.bs.modal', function () {
      $columnNameEl.focus().attr("autocomplete", "off");

      $columnNameEl.keyup(function (e) {
        validateInput($columnNameEl.val(), function () {
          $submit.prop('disabled', false);
          clearError($inputWrapper);
        }, function (msg) {
          $submit.prop('disabled', true);
          if (msg) {
            showError($inputWrapper, msg);
          }
        });
      });

      $('.js-name-form', $modalEl).submit(function () {
        var name = $columnNameEl.val().trim();
        callback(name);
        $modalEl.modal('hide');
        $columnNameEl.val('');
        return false;
      });
    });

    $modalEl.on('hide.bs.modal', function() {
      $columnNameEl.val('');
    });

    $modalEl.modal();
  }

  function insertColumn(hotInstance, selection) {
    hotInstance.deselectCell();
    getNewColumnName(function (name) {
      NVMetadata.headers.push({
        name: name
      });
      hotInstance.updateSettings({
        data: window.NVMetadata.data,
        colHeaders: headerNames(window.NVMetadata.headers),
        columns: columnSettings(NVMetadata.headers)
      });
      hotInstance.render();
    });
  }

  $(document).ready(function () {

    var container = document.getElementById('hot'),
      hot = new Handsontable(container, {
        data: window.NVMetadata.data,
        colHeaders: headerNames(window.NVMetadata.headers),
        columns: columnSettings(window.NVMetadata.headers),
        rowHeaders: true,
        height: getDefaultHeight(window.NVMetadata.data),
        contextMenu: {
          callback: function (key) {
            if (key === 'insert_column_left' ||
              key === 'insert_column_right') {
              insertColumn(hot, hot.getSelected());
            }
          },
          items: {
            'row_above': {},
            'row_below': {},
            'hsep1': '---------',
            'insert_column_left': {
              name: 'Insert column on the left'
            },
            'insert_column_right': {
              name: 'Insert column on the right'
            },
            'hsep2': '---------',
            'remove_row': {},
            'hsep3': '---------',
            'undo': {},
            'redo': {}
          }
        },
        cells: function (r, c, prop) {
          if (c === 0) {
            return {
              readOnly: true
            };
          }
        }
      });

    $('.btn-save-metadata').click(function () {
      $.ajax({
          type: 'POST',
          data: JSON.stringify(serializeTable(hot)),
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
      if (hot.isUndoAvailable()) {
        return 'You have pending unsaved changes. ' +
          'Do you really want to discard them ?';
      }
    };
  });

}(jQuery));
