function cloneMore(selector, type) {
    var newElement = $(selector).clone(true);
    var total = $('#id_' + type + '_set-TOTAL_FORMS').val();
    newElement.find(':input').each(function() {
        if ($(this).attr('name') == 'csrfmiddlewaretoken') return true;
        var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
        var id = 'id_' + name;
        $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
    });
    newElement.find('a').remove()  // Remove the filename
    newElement.find('label').each(function() {
        var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
        $(this).attr('for', newFor);
    });
    total++;
    $('#id_' + type + '_set-TOTAL_FORMS').val(total);
    $(selector).after(newElement);
}

var active_form, showForm, updateImageName;

active_form = 0;

showForm = function(id) {
  var name;
  $('.image-form').hide();
  active_form = id;
  $('.image-form#image-' + active_form).show();
  name = $("input#id_image_set-" + active_form + "-name").val();
  if (!name) {
    name = '[untitled image]';
  }
  updateImageName(name);
  return $("input#id_image_set-" + active_form + "-name").keyup(function(e) {
    var val;
    val = $(e.target).val();
    return updateImageName(val);
  });
};

updateImageName = function(name) {
  $('#current-image').text(name);
  return $("#image-select option[value='" + active_form + "']").text(name);
};

$(document).ready(function() {
  var num_forms;
  num_forms = $('.image-form').length;
  if (num_forms > 1) {
    $('.image-form').last().remove();
    $('#id_image_set-TOTAL_FORMS').val(num_forms - 1);
    $('#image-select li').last().remove()
  } else {
    $("#id_image_set-" + (num_forms - 1) + "-id").val('');
  }
  showForm(active_form);
  $('#image-select li').click(function(e) {
    e.preventDefault();
    $(this).siblings().removeClass('active');
    $(this).addClass('active');
    id = $(this).attr('id').replace('showform-image-','');
    return showForm(id);
  });
  $('#submit-form').click(function(e) {
    e.preventDefault();
    return $('form').submit();
  });
  $('#add-image-form').click(function(e) {
    var nextIndex;
    e.preventDefault();
    cloneMore('div.image-form:last', 'image');
    nextIndex = $('.image-form').length - 1;
    $('#image-select').append($('<option>', {
      value: nextIndex
    }).text('[untitled image]'));
    $('.image-form:last').attr('id', 'image-' + nextIndex);
    $('#image-select').val(nextIndex);
    return showForm(nextIndex);
  });
  return $("input[id$='image_ptr']").each(function() {
    if ($(this).val() === "None") {
      return $(this).val("");
    }
  });
});
