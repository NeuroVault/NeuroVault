/*global window, document, jQuery, Papa, Fuse, DataImport, NVMetadata */
(function ($) {
  'use strict';

  $.fn.loadFile = function (options) {

    var $fileInput = $('.fileInput', this);

    function isAllowedExtension(fileName) {
      var ext = (-1 !== fileName.indexOf('.')) ? fileName
        .replace(/.*[.]/, '').toLowerCase() : '',
        allowed = options.allowedExtensions,
        len = allowed.length,
        i;

      if (!len) {
        return true;
      }

      for (i = 0; i < len; i += 1) {
        if (allowed[i].toLowerCase() === ext) {
          return true;
        }
      }

      return false;
    }

    function listExtensions(extensions) {
      return extensions.join(', ');
    }

    function validate(file, opts) {
      var errors = [],
        msg;

      if (!isAllowedExtension(file.name)) {
        msg = '<strong>' + file.name +
          '</strong> has unsupported file type. Select a ';
        msg += listExtensions(options.allowedExtensions) + ' file.';

        errors.push({
          msg: msg
        });
      }

      if (errors.length) {
        opts.fail(errors);
      } else {
        opts.complete(file);
      }
    }

    $('.btn-upload', this).click(function () {
      $fileInput.click();
    });

    $fileInput.change(function () {
      validate(this.files[0], {
        complete: options.onload,
        fail: options.onfail,
      });
    });

    return this;
  };

  var is = DataImport.is,

    fields = [{
      id: 'Filename',
      name: 'Filename',
      required: true,
      validate: [
        is.unique(),
        is.matchingRegex(['.*(?:\\.nii(?:\\.gz)?|\\.img)$']),
      ]
    }, {
      id: 'Subject ID',
      name: 'Subject ID',
      required: true
    }, {
      id: 'Image Type',
      name: 'Image Type',
      required: true,
      choices: ['group', 'subject', 'item'],
      validate: [
        is.anyOf(['group', 'subject', 'item'],
          'Wrong value')
      ]
    }, {
      id: 'Sex',
      name: 'Sex',
      required: false,
      validate: [
        is.belongsToAnyOfSets([
          [0, 1],
          [1, 2],
          ['m', 'f'],
          ['male', 'female']
        ], 'Inconsistent values')
      ]
    }, {
      id: 'Age',
      name: 'Age',
      required: false,
    }],

    matchFields = function (fields, data) {
      var fuse = new Fuse(data[0]),
        mapping = [],
        obj = {},
        result,
        len,
        i;

      for (i = 0, len = fields.length; i < len; i += 1) {
        result = fuse.search(fields[i].id);
        if (result.length && !obj.hasOwnProperty(result[0])) {
          obj[result[0]] = fields[i].id;
        }
      }

      for (i = 0, len = data[0].length; i < len; i += 1) {
        mapping.push(obj[i] || null);
      }

      return mapping;
    },
    dataimport;

  function removeErrors($el) {
    $el.empty();
    $el.hide();
  }

  function showDataSheetStep() {
    $('.step-content .step1').removeClass('active');
    $('.step-content .step2').addClass('active');
  }

  function showUploadStep() {
    $('.step-content .step2').removeClass('active');
    $('.step-content .step1').addClass('active');
  }

  function openDataImport(results) {
    var $hot = $('#hot');

    if (results.errors.length) {
      NVMetadata.displayErrors($('.step1 .errors'), results.errors);
    }

    removeErrors($('.step2 .errors'));
    showDataSheetStep();

    // window.sheetModified = true;

    dataimport = new DataImport($hot[0], {
      fields: fields,
      data: results.data,
      sheetHeight: 400,
      matchFields: matchFields
    });
  }

  function parseCSV(file) {
    removeErrors($('.step1 .errors'));

    if (dataimport) {
      dataimport.destroy();
    }

    Papa.parse(file, {
      complete: openDataImport
    });
  }

  function getCollectionIdFromURL(url) {
    var match = url.match(/collections\/(\d+)/);
    if (match[1]) {
      return match[1];
    }
    return '';
  }

  function submitResult(result) {
    $.ajax({
      type: 'POST',
      data: JSON.stringify(result),
      contentType: 'application/json; charset=utf-8'
    })
      .done(function () {
        var collectionId = getCollectionIdFromURL(window.location.href);
        window.location.replace('/collections/' + collectionId);
      })
      .fail(function (jqXHR, textStatus, errorThrown) {
        NVMetadata.displayErrors($('.step2 .errors'),
          NVMetadata.getErrors(jqXHR, textStatus, errorThrown));
      });
  }

  $(document).ready(function () {
    $('.uploader').loadFile({
      allowedExtensions: ['csv'],
      onload: parseCSV,
      onfail: NVMetadata.displayErrors.bind(null, $('.step1 .errors'))
    });

    $('.step-content .btn-step-pane-back').click(function () {
      showUploadStep();
    });

    $('.btn-complete-import').click(function () {
      dataimport.validate({
        complete: function (result) {
          removeErrors($('.step2 .errors'));
          submitResult(result);
        },
        fail: function (errors) {
          NVMetadata.displayErrors($('.step2 .errors'), errors);
        }
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
