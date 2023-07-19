if (!String.prototype.format) {
    String.prototype.format = function () {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function (match, number) {
            return typeof args[number] != 'undefined'
                ? args[number]
                : match
                ;
        });
    };
}

function dateFormat(timestamp) {
    let wordEnd = function (value, ends = ["", "у", "ы"]) {
        let rem = value % 10;
        if ((10 < value && value < 20) || rem === 0 || rem >= 5) {
            return ends[0];
        } else if (rem === 1) {
            return ends[1];
        } else {
            return ends[2];
        }
    };
    let timeDiff = Math.trunc((Date.now() - timestamp) / 1000);
    if (timeDiff < 60) {
        return `${timeDiff} секунд${wordEnd(timeDiff)} назад`;
    } else if (timeDiff < 3600) {
        timeDiff = Math.trunc(timeDiff / 60);
        return `${timeDiff} минут${wordEnd(timeDiff)} назад`;
    } else if (timeDiff < 86400) {
        timeDiff = Math.trunc(timeDiff / 3600);
        return `${timeDiff} час${wordEnd(timeDiff, ['ов', '', 'а'])} назад`;
    } else {
        const options = {
            year: '2-digit', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        };
        const rtf = new Intl.DateTimeFormat('ru-RU', options);
        return rtf.format(new Date(timestamp * 1000));
    }
}

function updateDates() {
    $(".datetime").each(
        function (i, element) {
            let elem = $(element);
            let timestamp = parseInt(elem.attr("data-timestamp"));
            if (!Number.isNaN(timestamp)) elem.find("span").text(dateFormat(timestamp*1000));
        }
    )
}
setInterval(updateDates, 1000);

function changedAnim(selector) {
    anime({
        targets: selector,
        backgroundColor: [
            {value: '#F00', duration: 400},
            {value: 'rgba(255,255,255,0)', duration: 1300}
        ],
        color: [
            {value: '#FFF', duration: 400},
            {value: '#000', duration: 1300}
        ],
        easing: 'easeInExpo'
    });
}

function queryInfo(dataName, callback, value = "", fields = [], url = "/api/get_info") {
    $.ajax({
        url: url,
        type: 'post',
        data: JSON.stringify({name: dataName, value: value, fields: fields}),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        processData: false,
        success: callback,
    });
}

const miningCheckbox = document.getElementById('miningCheck')

miningCheckbox.addEventListener('change', (event) => {
    $.ajax({
        url: "/api/change_mining_status",
        type: 'post',
        data: JSON.stringify({status:event.currentTarget.checked}),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        processData: false,
        success: function (data) { if (!data.success) event.currentTarget.checked = !event.currentTarget.checked; }
    });
})

function updateMinerCheckbox() {
        $.ajax({
        url: "/api/get_mining_status",
        type: 'post',
        processData: false,
        success: function (data) { miningCheckbox.checked = data["status"]; }
    });
}

setInterval(updateMinerCheckbox, 5000)

document.addEventListener("DOMContentLoaded", function(event) {
    updateMinerCheckbox()
});