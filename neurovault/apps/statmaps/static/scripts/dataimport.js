/*global window, document, Handsontable */

(function (window, document, Handsontable) {
  'use strict';

  function Sheet(container, options) {
    options = options || {};
    this.mapping = options.mapping;
    this.fields = options.fields;
    this.data = options.data;
    this.afterColumnChange = options.afterColumnChange;
    this.height = options.height;

    var _this = this,
      boldRenderer,
      validationRenderer,
      columnChoices = {},
      markedCells = {};

    this.fieldById = options.fields.toObject();

    /**
     * Marked Cells
     */

    this.markCell = function (row, column) {
      markedCells[row + ',' + column] = true;
    };

    this.markCellsInColumn = function (column, rows) {
      var len,
        i;
      for (i = 0, len = rows.length; i < len; i += 1) {
        this.markCell(rows[i] + 1, column);
      }
    };

    this.clearMarkedCellsInColumn = function (column) {
      var len,
        i;
      for (i = 0, len = this.data.length; i < len; i += 1) {
        this.clearMark(i, column);
      }
    };

    this.clearMark = function (row, column) {
      delete markedCells[row + ',' + column];
    };

    this.clearMarkedCells = function () {
      markedCells = {};
    };

    function getChoicesForColumn(column) {
      return columnChoices[column];
    }

    function setChoicesForMapping(mapping) {
      var fieldId,
        choices,
        len,
        i;

      columnChoices = {};

      for (i = 0, len = mapping.length; i < len; i += 1) {
        fieldId = mapping[i];
        if (fieldId) {
          choices = _this.fieldById[fieldId].choices;

          if (choices) {
            columnChoices[i] = choices;
          }
        }
      }
    }

    setChoicesForMapping(this.mapping);

    /*jslint unparam: true */
    boldRenderer = function (instance, td, row, col, prop,
      value, cellProperties) {
      //jshint unused:false

      Handsontable.renderers.TextRenderer.apply(this, arguments);
      td.style.fontWeight = 'bold';
    };

    /*jslint unparam: true */
    validationRenderer = function (instance, td, row, col, prop,
      value, cellProperties) {
      //jshint unused:false

      Handsontable.renderers.TextRenderer.apply(this, arguments);

      if (markedCells[row + ',' + col]) {
        td.style.backgroundColor = '#ff4c42';
      }

      var choices = getChoicesForColumn(col);
      if (choices) {
        Handsontable.renderers.AutocompleteRenderer.apply(this, arguments);
        cellProperties.source = choices;
        cellProperties.editor = Handsontable.editors.DropdownEditor;
      } else {
        cellProperties.editor = 'text';
      }
    };

    /**
     * Dropdowns
     */

    function addButtonMenuEvent(button, menu) {

      Handsontable.Dom.addEvent(button, 'click', function (event) {
        var columnDropdownMenu, position, removeMenu, i, len;

        document.body.appendChild(menu);

        event.preventDefault();
        event.stopImmediatePropagation();

        if (menu.style.display === 'block') {
          menu.style.display = 'none';
          return;
        }

        columnDropdownMenu = document.querySelectorAll('.columnDropdownMenu');

        // Hide other menus
        for (i = 0, len = columnDropdownMenu.length; i < len; i += 1) {
          columnDropdownMenu[i].style.display = 'none';
        }

        // Show this menu
        menu.style.display = 'block';
        position = button.getBoundingClientRect();

        menu.style.top = (position.top +
          (window.scrollY || window.pageYOffset)) + 12 + 'px';
        menu.style.left = (position.left) + 'px';

        removeMenu = function (event) {
          if (event.target.nodeName === 'LI' && event.target.parentNode
            .className.indexOf('columnDropdownMenu') !== -1) {
            if (menu.parentNode) {
              menu.parentNode.removeChild(menu);
            }
          } else {
            columnDropdownMenu = document
              .querySelectorAll('.columnDropdownMenu');
            for (i = 0, len = columnDropdownMenu.length; i < len; i += 1) {
              columnDropdownMenu[i]
                .parentNode
                .removeChild(columnDropdownMenu[i]);
            }
          }
        };

        Handsontable.Dom.removeEvent(document, 'click', removeMenu);
        Handsontable.Dom.addEvent(document, 'click', removeMenu);
      });
    }

    function createListItem(options) {
      var li = document.createElement('LI');
      li.className = options.className;
      li.innerHTML = options.innerHTML;
      li.data = options.data;

      return li;
    }

    function buildMenu(items, activeId) {
      var
        menu = document.createElement('UL'),
        id;

      menu.className = 'columnDropdownMenu';

      for (id in items) {
        if (items.hasOwnProperty(id)) {
          menu.appendChild(createListItem({
            innerHTML: items[id].name,
            className: (activeId === id) ? 'active' : '',
            data: {
              'fieldId': id
            }
          }));
        }
      }

      menu.appendChild(createListItem({
        className: 'divider'
      }));

      menu.appendChild(createListItem({
        innerHTML: 'Reset Field',
        className: activeId ? '' : 'disabled',
        data: {
          'fieldId': null
        }
      }));

      return menu;
    }

    function setColumnMapping(columnIndex, fieldId, instance) {
      _this.mapping[columnIndex] = fieldId;

      setChoicesForMapping(_this.mapping);
      instance.render();
    }

    function getHeaderTitle(columnIndex, mapping, data) {
      var fieldId = mapping[columnIndex],
        name = 'None';

      if (fieldId) {
        name = _this.fieldById[fieldId].name;
      } else {
        if (data.length && data[0].length && data[0][columnIndex]) {
          name = data[0][columnIndex];
        }
        name = '<span style="color: gray;">' + name + '</span>';
      }

      return name;
    }

    /**
     * Handsontable Init
     */

    this.hot = new Handsontable(container, {
      stretchH: 'all',
      rowHeaders: true,
      data: _this.data,

      height: _this.height,

      contextMenu: true,
      manualColumnMove: false,

      colHeaders: function (col) {
        var name = getHeaderTitle(col, _this.mapping, _this.data);

        return '<button class="btn btn-default dropdown-toggle"' +
          ' type="button" id="dropdownMenu1" data-toggle="dropdown"' +
          ' aria-expanded="true">' + name +
          ' <span class="caret"></span></button>';
      },

      afterChange: function (changes, source) {
        if (source !== 'loadData') {
          var obj = {},
            col,
            len,
            i;

          for (i = 0, len = changes.length; i < len; i += 1) {
            obj[changes[i][1]] = true;
          }

          for (col in obj) {
            if (obj.hasOwnProperty(col)) {
              _this.afterColumnChange(col);
            }
          }
        }
      },

      afterGetColHeader: function (col, TH) {
        if (col < 0) {
          return;
        }

        var instance = this,
          menu = buildMenu(_this.fieldById, _this.mapping[col]);
        addButtonMenuEvent(TH.firstChild.firstChild.firstChild, menu);

        Handsontable.Dom.addEvent(menu, 'click', function (event) {
          if (event.target.nodeName === 'LI') {
            setColumnMapping(col, event.target.data.fieldId, instance);
          }
        });
      },

      afterCreateCol: function (index, amount) {
        if (amount === 1) {
          _this.mapping.splice(index, 0, null);
        } else {
          var args = [index, 0],
            i;

          for (i = 0; i < amount; i += 1) {
            args.push(null);
          }

          _this.mapping.splice.apply(_this.mapping, args);
        }
      },

      afterRemoveCol: function (index, amount) {
        _this.mapping.splice(index, amount);
      },

      // afterColumnMove: function (oldIndex, newIndex) {
      //   console.log('afterColumnMove', oldIndex, newIndex);
      //   if (oldIndex === newIndex) {
      //     return;
      //   }
      //   var temp = _this.mapping.splice(oldIndex, 1);
      //   _this.mapping.splice(newIndex, 0, temp[0]);
      // },

      cells: function (r) {
        if (r === 0) {
          this.renderer = boldRenderer;
        } else {
          this.renderer = validationRenderer;
        }
      }
    });
  }

  Sheet.prototype.render = function () {
    return this.hot.render();
  };

  Sheet.prototype.getData = function () {
    return this.hot.getData();
  };

  Sheet.prototype.getMapping = function () {
    return this.mapping;
  };

  Sheet.prototype.destroy = function () {
    this.hot.destroy();
  };

  window.Sheet = Sheet;

}(window, document, Handsontable));

/*global window, Sheet, Fuse*/

(function (window, Sheet) {
  'use strict';

  var DataImport = function (containerElement, options) {
    options = options || {};
    this.data = options.data;
    this.fields = options.fields;
    this.sheetHeight = options.sheetHeight;

    function mapFields(fields, data) {
      var fuse = new Fuse(fields, {
          keys: ['name']
        }),

        mapping = data[0].map(function (x) {
          var result = fuse.search(x);

          if (result.length) {
            return result[0].id;
          }

          return null;
        });

      return mapping;
    }

    this.fields.toObject = function () {
      var len = this.length,
        obj = {},
        i;

      for (i = 0; i < len; i += 1) {
        obj[this[i].id] = this[i];
      }

      return obj;
    };

    var mapping = mapFields(this.fields, this.data),
      _this = this;

    this.sheet = new Sheet(containerElement, {
      mapping: mapping,
      fields: this.fields,
      data: this.data,
      height: this.sheetHeight,
      afterColumnChange: function (columnIndex) {
        _this.sheet.clearMarkedCellsInColumn(columnIndex);
        _this.validateColumn(columnIndex);
        _this.sheet.render();
      }
    });
  };

  function mergeHeaders(firstRow, mapping) {
    var i = 0;

    return firstRow.map(function (value) {
      if (mapping[i]) {
        value = mapping[i];
      }
      i += 1;
      return value;
    });
  }

  DataImport.prototype.getFieldByColumnIndex = function (columnIndex) {
    var fieldById = this.fields.toObject(),
      headers = mergeHeaders(this.sheet.getData()[0], this.sheet.getMapping());

    return fieldById[headers[columnIndex]];
  };

  DataImport.prototype.validateColumn = function (columnIndex) {
    var field = this.getFieldByColumnIndex(columnIndex),
      errors = [],
      data,
      validate,
      error,
      len,
      i;

    if (field && field.validate) {
      validate = field.validate;
      data = this.sheet.getData();

      for (i = 0, len = validate.length; i < len; i += 1) {
        error = validate[i](data, field, columnIndex);
        if (error) {
          errors.push({
            msg: error.msg + ' in field "' + field.id + '"'
          });
          this.sheet.markCellsInColumn(columnIndex, error.rows);
        }
      }
    }

    return errors;
  };

  DataImport.prototype.validate = function (options) {
    options = options || {};

    var data = this.sheet.getData(),
      headers = mergeHeaders(data[0], this.sheet.getMapping()),
      validators = DataImport.validators,
      errors = [],
      error,
      len,
      i;

    this.sheet.clearMarkedCells();
    this.sheet.render();

    data = data.slice(1);
    data.unshift(headers);

    for (i = 0, len = validators.length; i < len; i += 1) {
      error = validators[i](data, this.fields);
      if (error) {
        errors.push(error);
      }
    }

    if (!errors.length) {
      for (i = 0, len = headers.length; i < len; i += 1) {
        errors = errors.concat(this.validateColumn(i));
      }

      this.sheet.render();
    }

    if (errors.length) {
      options.fail(errors);
    } else {
      options.complete(data);
    }
  };

  DataImport.prototype.destroy = function () {
    this.sheet.destroy();
  };

  window.DataImport = DataImport;

}(window, Sheet, Fuse));

/*global DataImport */

(function (DataImport) {
  'use strict';
  var validators = [];

  function findDuplicateItems(array) {
    var obj = {},
      result = [],
      indexList,
      value,
      len,
      i;

    for (i = 0, len = array.length; i < len; i += 1) {
      indexList = obj[array[i]];
      if (!indexList) {
        obj[array[i]] = indexList = [];
      }
      indexList.push(i);
    }

    for (value in obj) {
      if (obj.hasOwnProperty(value)) {
        indexList = obj[value];
        len = indexList.length;
        if (len > 1) {
          for (i = 0; i < len; i += 1) {
            result.push({
              value: value,
              row: indexList[i]
            });
          }
        }
      }
    }

    return result;
  }

  function findMissingFields(headers, fieldList) {
    var result = [],
      obj = {},
      field,
      fieldId,
      len,
      i;

    for (i = 0, len = fieldList.length; i < len; i += 1) {
      field = fieldList[i];
      if (field.required) {
        obj[field.id] = true;
      }
    }

    for (i = 0, len = headers.length; i < len; i += 1) {
      delete obj[headers[i]];
    }

    for (fieldId in obj) {
      if (obj.hasOwnProperty(fieldId)) {
        result.push(fieldId);
      }
    }

    return result;
  }

  function findFieldsWithMissingValues(data) {
    var result = [],
      obj = {},
      leni,
      lenj,
      column,
      i,
      j;

    for (i = 0, leni = data.length; i < leni; i += 1) {
      for (j = 0, lenj = data[i].length; j < lenj; j += 1) {
        if (data[i][j] === '') {
          column = obj[j];
          if (!column) {
            obj[j] = column = [];
          }
          column.push(i);
        }
      }
    }

    for (j in obj) {
      if (obj.hasOwnProperty(j)) {
        result.push({
          id: data[0][j],
          index: j,
          emptyRows: obj[j]
        });
      }
    }

    return result;
  }

  function getColumnValues(data, columnIndex) {
    var columnValues = [],
      len,
      i;
    for (i = 1, len = data.length; i < len; i += 1) {
      columnValues.push(data[i][columnIndex]);
    }
    return columnValues;
  }

  function pluralizeEn(num, singular, plural) {
    return (num !== 1) ? plural : singular;
  }

  /**
   * Check for duplicate columns
   *
   * @param {Array} data
   */

  function checkDuplicates(data) {
    var duplicates = findDuplicateItems(data[0]),
      items = [],
      obj = {},
      value,
      msg,
      len,
      i;

    if (duplicates.length) {
      for (i = 0, len = duplicates.length; i < len; i += 1) {
        obj[duplicates[i].value] = true;
      }

      duplicates = [];

      for (value in obj) {
        if (obj.hasOwnProperty(value)) {
          duplicates.push(value);
        }
      }

      msg = pluralizeEn(duplicates.length, 'Duplicate field',
        'Duplicate fields');

      items = [];
      for (i = 0, len = duplicates.length; i < len; i += 1) {
        items.push('"' + duplicates[i] + '"');
      }

      msg += ' ' + items.join(', ');

      return {
        msg: msg
      };
    }
  }

  function arrayToSet(array) {
    var obj = {},
      len,
      i;

    for (i = 0, len = array.length; i < len; i += 1) {
      obj[array[i]] = true;
    }

    return obj;
  }

  function substractSet(setA, setB) {
    var result = [],
      value;

    for (value in setA) {
      if (setA.hasOwnProperty(value) && setB[value] === undefined) {
        result.push(value);
      }
    }

    return result;
  }

  /**
   * Check if all required columns present
   *
   * @param {Array} data
   * @param {Array} fields
   */
  function checkMissingFields(data, fields) {
    var missing = findMissingFields(data[0], fields),
      items = [],
      msg,
      i;

    if (missing.length) {
      msg = pluralizeEn(missing.length, 'Missing field',
        'Missing fields');

      for (i = 0; i < missing.length; i += 1) {
        items.push('"' + missing[i] + '"');
      }

      msg += ' ' + items.join(', ');

      return {
        msg: msg
      };
    }
  }

  /**
   * Check for missing values in columns
   *
   * @param {Array} data
   * @param {Array} fields
   */
  function checkMissingValues(data) {
    var missing = findFieldsWithMissingValues(data),
      items = [],
      msg,
      i;

    if (missing.length) {
      msg = pluralizeEn(missing.length,
        'Missing values in field',
        'Missing values in fields');

      for (i = 0; i < missing.length; i += 1) {
        items.push('"' + missing[i].id + '"');
      }

      msg += ' ' + items.join(', ');

      return {
        msg: msg
      };
    }
  }

  function findRegexMatchExceptions(regex, columnValues) {
    var noMatch = [],
      value,
      len,
      i;

    for (i = 0, len = columnValues.length; i < len; i += 1) {
      value = columnValues[i] || '';
      if (!value.match(regex)) {
        noMatch.push({
          value: value,
          row: i
        });
      }
    }

    return noMatch;
  }

  function findStringMatchExceptions(array, columnValues) {
    var noMatch = [],
      value,
      len,
      i;

    for (i = 0, len = columnValues.length; i < len; i += 1) {
      value = columnValues[i];
      if (array.indexOf(value) === -1) {
        noMatch.push({
          value: value,
          row: i
        });
      }
    }

    return noMatch;
  }

  function pluck(collection, key) {
    return collection.map(function (obj) {
      return obj[key];
    });
  }

  function range(end) {
    var result = [],
      i;

    for (i = 0; i <= end; i += 1) {
      result.push(i);
    }

    return result;
  }

  DataImport.is = {};

  /**
   * Check for unique values in columns
   *
   * @param {String} message
   */

  DataImport.is.unique = function (message) {
    message = message || 'Duplicate values';

    function validate(data, field, columnIndex) {
      var columnValues = getColumnValues(data, columnIndex),
        duplicates = findDuplicateItems(columnValues);

      if (duplicates.length) {
        return {
          msg: message,
          rows: pluck(duplicates, 'row')
        };
      }
    }

    return validate;
  };

  /**
   * Check for values matching regex
   *
   * @param {Array} regExpAndFlags
   * @param {String} message
   */

  DataImport.is.matchingRegex = function (regExpAndFlags, message) {
    message = message || 'Wrong value format';

    var regex = new RegExp(regExpAndFlags[0], regExpAndFlags[1]);

    function validate(data, field, columnIndex) {
      var columnValues = getColumnValues(data, columnIndex),
        matchExceptions = findRegexMatchExceptions(
          regex,
          columnValues
        );

      if (matchExceptions.length) {
        return {
          msg: message,
          rows: pluck(matchExceptions, 'row')
        };
      }
    }

    return validate;
  };

  /**
   * Check is column values are subset of a specific set
   *
   * @param {Array} arrayOfArrays
   * @param {String} message
   */

  DataImport.is.belongsToAnyOfSets = function (arrayOfArrays, message) {
    function validate(data, field, columnIndex) {
      var columnValues = getColumnValues(data, columnIndex),
        valueSet = arrayToSet(columnValues),
        optionSet,
        missingValues,
        len,
        i;

      for (i = 0, len = arrayOfArrays.length; i < len; i += 1) {
        optionSet = arrayToSet(arrayOfArrays[i]);
        missingValues = substractSet(valueSet, optionSet);
        if (!missingValues.length) {
          break;
        }
      }

      if (missingValues.length) {
        return {
          msg: message,
          rows: range(columnValues.length)
        };
      }
    }

    return validate;
  };

  /**
   * Check for values matching any of given string in a set.
   *
   * @param {Array} array
   * @param {String} message
   */

  DataImport.is.anyOf = function (array, message) {
    function validate(data, field, columnIndex) {
      var columnValues = getColumnValues(data, columnIndex),
        matchExceptions = findStringMatchExceptions(
          array,
          columnValues
        );

      if (matchExceptions.length) {
        return {
          msg: message,
          rows: pluck(matchExceptions, 'row')
        };
      }
    }

    return validate;
  };

  validators.push(checkDuplicates);
  validators.push(checkMissingFields);
  validators.push(checkMissingValues);

  DataImport.validators = validators;

}(DataImport));
