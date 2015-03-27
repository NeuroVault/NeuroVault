/*global window, document, jQuery, Papa, DataImport */
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
      id: 'File Name',
      name: 'File Name',
      required: true,
      validate: [
        is.unique(),
        is.matchingRegex(['.*(?:\\.nii(?:\\.gz)?|\\.img)$']),
      ]
    }, {
      id: 'Subject Id',
      name: 'Subject Id',
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
    dataimport;


  function displayErrors($el, errors) {
    var  len = errors.length,
      i;

    $el.empty();

    for (i = 0; i < len; i += 1) {
      $el.append('<div>' + errors[i].msg + '</div>');
    }
    $el.show();
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
      displayErrors($('.step1 .errors'), results.errors);
    }

    showDataSheetStep();
    // window.sheetModified = true;

    dataimport = new DataImport($hot[0], {
      fields: fields,
      data: results.data,
      sheetHeight: 400
    });
  }

  function parseCSV(file) {
    Papa.parse(file, {
      complete: openDataImport
    });
  }

  function submitResult(result) {
    console.log(result);
  }

  $(document).ready(function () {
    $('.uploader').loadFile({
      allowedExtensions: ['csv'],
      onload: parseCSV,
      onfail: displayErrors.bind(null, $('.step1 .errors'))
    });

    $('.step-content .btn-step-pane-back').click(function () {
      showUploadStep();
    });

    $('.btn-complete-import').click(function () {
      dataimport.validate({
        complete: function (result) {
          submitResult(result);
        },
        fail: function (errors) {
          displayErrors($('.step2 .errors'), errors);
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
