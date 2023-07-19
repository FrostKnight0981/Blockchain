$('.custom-file-input').on('change', function (e) {
    let fileName = $(this).val();
    $(this).next('.custom-file-label').html(fileName);
})


$('#login_button').on('click', function (e) {
    let file = $("#inputGroupFile01")[0].files[0];
    if (typeof file === 'undefined') {
        alert("Выберите файл.")
        return;
    }
    let form_data = new FormData();
    form_data.append("file", file)

    $.ajax({
        url: '/api/login',
        type: 'post',
        data: form_data,
        contentType: false,
        processData: false,
        success: function (response) {
            if (response !== 0) {
                if (response["success"])
                    location.reload()
                else
                    alert(response["error"])
            } else {
                alert('file not uploaded');
            }
        },
    });
})