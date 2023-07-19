updateChainInfo();
setInterval(updateChainInfo, 1000);

function updateBlocks(chain_length) {
    const data = "<div class=\"content row\" style='visibility: collapse'>" +
        "<div class=\"col-2\">" +
        "<a class=\"block-index\" href=''></a></div>" +
        "<div class=\"col-5 datetime\" data-timestamp=\"0\">" +
        "<span></span>" + // Date
        "</div>" +
        "<div class=\"col-3\">" +
        "<span class='block-size'></span>"+
        "</div>" +
        "<div class=\"col-2\">" +
        "<span class='block-tx-count'></span>" +
        "</div>" +
        "</div>";
    const root = $("#last_block_list");
    if (root.children().length === 0){
        for (let i = 0; i < 5; i++) {
            root.prepend(data);
        }
    }
    let index_link = root.find(".block-index").first();
    if (index_link.length === 0 || parseInt(index_link.text()) !== chain_length - 1 ){
        root.children().each(
            function (index, element) {
                let block_index = chain_length - index - 1;
                if (block_index >= 0) {
                    addBlock($(element), block_index);
                }
            }
        );
    }
}
function addBlock(container, index){
    queryInfo("block",
    function (response) {
        let index_link = container.find(".block-index").first();
        index_link.attr('href', '/block/' + response["index"]);
        index_link.text(response["index"]);

        let timestamp = container.find(".datetime").first();
        timestamp.attr("data-timestamp", response["timestamp"]);
        timestamp.find("span").text(dateFormat(response["timestamp"]*1000));

        let size = container.find(".block-size").first();
        size.text(response["size"]);

        let count_tx = container.find(".block-tx-count").first();
        count_tx.text(response["count_tx"]);

        if (index % 2 === 0) {
            container.removeClass("odd-content");
            container.addClass("content");
        }
        else {
            container.removeClass("content");
            container.addClass("odd-content");
        }
        container.css("visibility", "visible");
    }, index, ["index", "timestamp", "size", "count_tx"]);
}


function updateChainInfo() {
    const base_row = "<div class=\"row border-bottom\"><div class=\"col-5 col-sm-5 col-md-4 font-weight-bold text-secondary text-truncate\">" +
        "{0}</div>";
    const value_part = "<div class=\"col-7 col-sm-7 col-md-8 text-truncate\"><span id=\"{0}\">{1}</span></div></div>";
    const date_part = "<div id=\"{0}\" class=\"col-7 col-sm-7 col-md-8 text-truncate datetime\" data-timestamp=\"{1}\">" +
        "<span>{2}</span></div></div>";
    const rootElement = $(".info-list").first();
    const keyToText = {
        "branch_count": "Количество ветвей",
        "chain_length": "Длина",
        "first_block_date": "Дата создания генезиса",
        "node_count": "Количество узлов",
        "pool_length": "Длина пула транзакций",
        "difficulty": "Сложность",
        "transaction_count": "Количество транзакций",
        "file_count": "Количество файлов",
        "account_count": "Количество аккаунтов",
        "weight": "Вес",
        "cost": "Цена"
    }
    queryInfo("chain",
        function (data) {
            for (const [key, value] of Object.entries(data)) {
                let valueContainer = rootElement.find("#" + key).first();
                if (key === "chain_length") updateBlocks(value);
                if (valueContainer.length === 0) {
                    rootElement.append(base_row.format(keyToText[key]) +
                        (key === "first_block_date" ? date_part.format(key, value, dateFormat(value*1000))
                            : value_part.format(key, value)));
                } else {
                    if (key === "first_block_date") {
                        valueContainer.attr("data-timestamp", value);
                    }
                    else {
                        if (valueContainer.text() !== value.toString()) {
                            valueContainer.text(value);
                            changedAnim("#" + key);
                        }
                    }
                }
            }
        });
}