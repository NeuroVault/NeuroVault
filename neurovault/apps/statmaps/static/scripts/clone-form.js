var active_form, showForm, updateImageName, cloneMore;

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

cloneMore = function (selector, type, imgtype) {
  var newElement = $(selector).clone(true);
  var total = $('#id_' + type + '_set-TOTAL_FORMS').val();
  newElement.children().each(function(n,ele) {
    if($(this).attr('type') == 'hidden') return true;
    $(this).remove();
  });

  newElement.find(':input').each(function() {
    if ($(this).attr('name') == 'csrfmiddlewaretoken') return true;
    var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
    var id = 'id_' + name;
    $(this).attr({'name': name, 'id': id}).removeAttr('checked');
    if($(this).attr('name').search('collection') > -1) return true;
    $(this).val('')
  });

  $('#blank_'+imgtype).children().each(function() {
    if($(this).attr('id').search('collection') > -1) return true;
    newElement.append($(this).clone(true));
  });

  newElement.find('div.control-group').each(function(n,n_ele) {
    rname = $(this).attr('id').replace('div_id_','');
    name = type + '_set-' + (total) + '-' + rname;
    $(n_ele).attr('id', $(this).attr('id').replace(rname,name));
    $(n_ele).find('label').each(function(n,ele) {
      $(ele).attr('for', $(ele).attr('for').replace(rname,name));
    });
    $.each(['input','select','textarea'], function(i, etype) {
      $(n_ele).find(etype).each(function(n,ele) {
        $(ele).attr('id', $(ele).attr('id').replace(rname,name));
        $(ele).attr('name', $(ele).attr('name').replace(rname,name));
      });
    });
  });

  total++;
  $('#id_' + type + '_set-TOTAL_FORMS').val(total);
  $(selector).after(newElement);
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
    return $('#formset').submit();
  });
  $('#add-image-form').click(function(e) {
    e.preventDefault();
    var nextIndex;
    var newType = e.target.href.split('#')[1];
    cloneMore('div.image-form:last', 'image', newType);
    nextIndex = $('.image-form').length - 1;
    $('#image-select').append($('<li id="showform-image-'+nextIndex+'"><a href="#"><i class="icon-file-alt"></i>&nbsp;[new image]</a></li>'));
    $('.image-form:last').attr('id', 'image-' + nextIndex);
    $('#image-select li:last').siblings().removeClass('active');
    $('#image-select li:last').addClass('active');
    return showForm(nextIndex);
  });

  return $("input[id$='image_ptr']").each(function() {
    if ($(this).val() === "None") {
      return $(this).val("");
    }
  });
});

