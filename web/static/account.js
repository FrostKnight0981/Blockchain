filecontent = ""
$("#create_transaction").click( function (event) {
    let value = Math.trunc(parseFloat($("#tx_value").first().val()) * 10**9);
    if (isNaN(value)) {
        value = 0;
    }
    let encrypted = $("#encrypt").first()[0].checked;
    let to_verify = $("#to_verify_base").first()[0].checked;
    let receiver = $("#receiver").first().val();
    let filename = $("#sendFile").val().replace(/C:\\fakepath\\/i, '');
    let start_content_index = filecontent.search("base64,") + 7;
    let clearcontent = filecontent.slice(start_content_index)
    $.ajax({
        url: "/api/send_tx",
        type: 'post',
        data: JSON.stringify({"file": {"filename": filename, "content": clearcontent}, "value": value, "receiver": receiver,
                                    "encrypt": encrypted, "in_verify_base": to_verify}),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        processData: false,
        success: function (data) {
            if (data["success"]) {
                alert("Транзакция успешно добавлена в пулл.");
            } else {
                alert("Ошибка:" + data["error"]);
            }
        },
    });
    event.preventDefault();
})

setInterval(async () => {
    let fileinput = $("#sendFile");
    if (fileinput.prop('files')[0] !== undefined && fileinput.prop("files")[0] !== null)
        filecontent = await getBase64(fileinput.prop('files')[0])
}, 1000);

async function getBase64(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
  });
}

$('#verifyButton').on('click', function (e) {
    let file = $("#verifyFile")[0].files[0];
    if (typeof file === 'undefined') {
        alert("Выберите файл.")
        return;
    }
    let form_data = new FormData();
    form_data.append("file", file)

    $.ajax({
        url: '/file_verify',
        type: 'post',
        data: form_data,
        contentType: false,
        processData: false,
        success: function (response) {
            if (response !== 0) {
                if (response["verify"])
                    alert("Файл не был найден в системе.")
                else
                    alert("Такой файл уже находится в системе.\n Файл принадлежит: " + response["account"])
            } else {
                alert('Файл не был загружен');
            }
        },
    });
})
