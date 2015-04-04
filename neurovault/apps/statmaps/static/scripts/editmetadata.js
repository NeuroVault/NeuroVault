/*global window, document, jQuery, Handsontable */
(function ($) {
  'use strict';

  $(document).ready(function () {

    window.onbeforeunload = function () {
      if (window.sheetModified) {
        return 'You have pending unsaved changes. ' +
          'Do you really want to discard them ?';
      }
    };

    var container = document.getElementById('hot'),
      hot = new Handsontable(container, {
        data: window.NVMetadata,
        colHeaders: true,
        contextMenu: true,
        height: 400
      });


  });

}(jQuery));
