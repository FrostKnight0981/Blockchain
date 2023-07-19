setInterval(
    function () {
        let nb = $("#next-block");
        if (nb.children().length === 0) {
            queryInfo("block", function (response) {
                if (response["next_block"] !== null) {
                    nb.empty();
                    nb.append(`<a href=\"/block/${response["next_block"]}\">${response["next_block"]}</a>`);
                    changedAnim("#next-block a");
                }
            }, parseInt($("#block-index").text()), ["next_block"]);
        }
    }, 1000
)