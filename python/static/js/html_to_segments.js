
/**
 * @param {any} body
 */
async function fix_it_api(body) {

    const options = {
        headers: { "Content-Type": "application/json" },
        method: 'POST',
        dataType: 'json',
        body: JSON.stringify(body),
        // dispatcher: new Agent({ connect: { timeout: 60_000 } })
    };
    const response = await fetch('/HtmltoSegments', options);
    if (!response.ok) {
        console.error(response.statusText);
        return "";
    }
    const data = await response.json();

    const result = data.result;

    return result;
}

/**
 * @param {number} start_time
 * @param {string} id
 */
function do_seconds(start_time, id) {
    const time = new Date().getSeconds() - start_time;

    $(id).text("in " + time + " Seconds");
    return time;
}

function fix_it() {
    var start_time = new Date().getSeconds();
    $("#load_fixit").show();

    let sort_attrs = $("#sort_attrs").prop("checked");
    let wrap_sections = $("#wrap_sections").prop("checked");
    var text = $("#source_text").val();
    if (!text) {
        $("#load_fixit").hide();
        $("#new_text").val("no text");
        return;
    }

    (async () => {
        const newtext = await fix_it_api({ html: text, sort_attrs: sort_attrs, wrap_sections: wrap_sections });
        $("#new_text").val(newtext);
        $("#load_fixit").hide();
        do_seconds(start_time, "#time_fixit");

    })();
}
