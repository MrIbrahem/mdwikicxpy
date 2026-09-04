var express = require("express");
var cors = require('cors');
var body_parser = require('body-parser');
var u = require('./lib/d/u.js');

var app = express();

app.use(cors())

app.use(body_parser.json({ limit: '50mb' }));
app.use(body_parser.urlencoded({ limit: '50mb', extended: false }));

app.post("/textp", (req, res) => {
	const source_html = req.body.html;

	if (!source_html || source_html.trim().length === 0) {
		res.send({
			result: 'Content for translate is not given or is empty'
		});
		res.status(500).end();
		return;
	}
	try {
		const processed_text = u.tet(source_html);
		res.send({ result: processed_text });
	} catch (error) {
		console.error(error);
		res.send({
			result: error.message
		});
		res.status(500).end();
	}
	// res.send(processed_text);

});

app.listen(process.env.PORT || 8000, function () {
	console.log("Node.js app is listening on port " + (process.env.PORT || 8000));
});

