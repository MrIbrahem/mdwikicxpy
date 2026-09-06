
async function get_text_api_new(ty, title) {
    const options = {
        method: 'GET',
        dataType: 'json',
    };
    const response = await fetch('/' + ty + '/' + title, options);

    const result = await response.json();

    return result.result;
}

async function fix_it_api(text) {

    const options = {
        headers: { "Content-Type": "application/json" },
        method: 'POST',
        dataType: 'json',
        body: JSON.stringify({ html: text }),
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

function do_seconds(start_time, id) {
    const time = new Date().getSeconds() - start_time;

    $(id).text("in " + time + " Seconds");
    return time;
}

function fix_it() {
    var start_time = new Date().getSeconds();
    $("#load_fixit").show();

    var text = $("#old_domain").val();
    if (!text) {
        $("#load_fixit").hide();
        $("#new").val("no text");
        return;
    }

    (async () => {
        const newtext = await fix_it_api(text);
        $("#new").val(newtext);
        $("#load_fixit").hide();
        do_seconds(start_time, "#time_fixit");

    })();
}

function get_Fixed() {
    var start_time = new Date().getSeconds();
    $("#load_Fixed").show();

    var title = $("#title").val();
    (async () => {
        const oldtext = await get_text_api_new("page", title);

        $("#fixed_text").val(oldtext);

        $("#load_Fixed").hide();
        do_seconds(start_time, "#time_Fixed");

    })();
}
const domain_done = {};

function get_html_domain(tu) {
    var start_time = new Date().getSeconds();
    $("#load_" + tu).show();

    var title = String($("#title_" + tu).val());
    var domain = $("#domain_" + tu).val();
    // if domain == medwiki.toolforge.org and title not startswith "md:" then add it
    if (domain === "medwiki.toolforge.org" &&
        title.indexOf("Md:") !== 0 &&
        title.indexOf("md:") !== 0) {
        title = "Md:" + title;
    }
    (async () => {
        var ty = "PageHtmlDomain/" + domain;
        const oldtext = await get_text_api_new(ty, title);
        $("#old_" + tu).val(oldtext);
        $("#load_" + tu).hide();
        // ---
        var time = do_seconds(start_time, "#time_" + tu);
        // ---
        var link = $("<a></a>").attr("id", domain).attr("href", "https://" + domain + "/wiki/" + title).attr("target", "_blank");
        link.text(domain + " (" + time + "s)");
        // ---
        // if domain in domain_done or create one
        if (domain_done[domain]) {
            $("#" + domain).html(link);

        } else {
            domain_done[domain] = true;
            // ---
            $("#link_" + tu).append(link);
        }
    })();
}
