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