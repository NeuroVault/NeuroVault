var active_form, showForm, updateImageName, cloneMore, mapNavLink, getLastTextNode, formIsClean;

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

  if($('#empty_collection_msg').is(":visible")) {
    $('#empty_collection_msg').hide();
  }
  $('#id_image_set-' + active_form + '-cognitive_paradigm_cogatlas').css("width", "400px");
  $('#id_image_set-' + active_form + '-cognitive_paradigm_cogatlas').select2({ dropdownAutoWidth : true});

  return $("input#id_image_set-" + active_form + "-name").keyup(function(e) {
    var val;
    val = $(e.target).val();
    return updateImageName(val);
  });
};

getLastTextNode = function(selector) {
  return $(selector).contents().filter(function() {
    return this.nodeType == 3;
  }).last();
};

updateImageName = function(name) {
  $('#current-image').text(name);
  return getLastTextNode('#image-select li#showform-image-' + active_form + ' a').replaceWith('&nbsp;' + name);
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
      	if ($(ele).attr('id')){
          $(ele).attr('id', $(ele).attr('id').replace(rname,name));
          $(ele).attr('name', $(ele).attr('name').replace(rname,name));
      	}
      });
    });
  });
  
  total++;
  $('#id_' + type + '_set-TOTAL_FORMS').val(total);

  if(total === 1) {
    $(selector).replaceWith(newElement);
  } else {
    $(selector).after(newElement);
  }
};

mapNavLink = function(ele) {
  $(ele).siblings().removeClass('active');
  $(ele).addClass('active');
  id = $(ele).attr('id').replace('showform-image-','');
  return showForm(id);
};

formIsClean = function(sele) {
  if(typeof sele === "undefined") {
    sele = '.image-form';
  }
  if($(sele).find('div.errors').length === 0 && 
        $(sele).find('div.error').length === 0 &&
        $(sele).find('div.alert-error').length === 0) {
    return true;
  } else {
    return false;
  }
};

$(document).ready(function() {

  $('#image-select li').click(function(e) {
    e.preventDefault();
    mapNavLink(this);
  });

  $('#submit-form').click(function(e) {
    e.preventDefault();
    ret = $('#formset').submit();
    
    $('.image-form').each(function(ele) {
	    if(!formIsClean('.image-form#' + $(this).attr('id'))) {
	    	$($('#showform-' + $(this).attr('id')).children()[0]).css('color', '#b94a48')
	    }
    });
    return ret;
  });

  $('#add-image-form').click(function(e) {
    e.preventDefault();
    var nextIndex;
    var newType = e.target.href.split('#')[1];

    if(newType == 'zip') return uploadZip();
    cloneMore('div.image-form:last', 'image', newType);
    nextIndex = $('.image-form').length - 1;
    $('#image-select').append($('<li id="showform-image-'+nextIndex+'"><a href="#"><i class="icon-file-alt"></i>&nbsp;[new image]</a></li>'));
    $('.image-form:last').attr('id', 'image-' + nextIndex);
    $('#image-select li:last').siblings().removeClass('active');
    $('#image-select li:last').addClass('active');
    $('#image-select li:last').click(function(e) {
      e.preventDefault();
      mapNavLink(this);
    });

    return showForm(nextIndex);
  });

  var num_forms = $('.image-form').length;

  // extra blank form isn't sent when there are errors

  if (num_forms > 1 && formIsClean()) {
    $('.image-form').last().remove();
    $('#id_image_set-TOTAL_FORMS').val(num_forms - 1);
    $('#image-select li').last().remove()
  }

  if(num_forms === 1 && formIsClean()) {
    $("#id_image_set-" + (num_forms - 1) + "-id").val('');
  }
  
  //paint invalid forms red
  $('.image-form').each(function(ele) {
	    if(!formIsClean('.image-form#' + $(this).attr('id'))) {
	    	$($('#showform-' + $(this).attr('id')).children()[0]).css('color', '#b94a48')
	    }
  });

  // focus first error on any form
  $('.image-form').each(function(ele) {
    if(!formIsClean('.image-form#' + $(this).attr('id'))) {
      return mapNavLink($('#showform-' + $(this).attr('id')));
    }
  });
  
  showForm(active_form);

  // populate 'no images' view for completely empty collection

  if( !$('input#id_image_set-0-id').val() && num_forms === 1 && formIsClean()) {
    $('.image-form').last().hide();
    $('#id_image_set-TOTAL_FORMS').val(num_forms - 1);
    $('#image-select li').last().remove();
    $('#current-image').text('no images');
    $('#empty_collection_msg').show();
  }

  return $("input[id$='image_ptr']").each(function() {
    if ($(this).val() === "None") {
      return $(this).val("");
    }
  });

});

