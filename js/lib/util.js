/**
 * @external Application
 * @external Request
 * @external Router
 */

import { readFileSync } from 'fs';
import { load } from 'js-yaml';
import language_data from '@wikimedia/language-data';

/**
 * Error instance wrapping HTTP error responses
 */
class HTTPError extends Error {

	constructor(response) {
		super();
		Error.capture_stack_trace(this, HTTPError);

		this.name = this.constructor.name;
		this.message = `${response.status}`;
		if (response.detail) {
			this.message += `: ${response.detail}`;
		}

		if (response.type) {
			this.message += `: ${response.type}`;
		}

		Object.assign(this, response);
	}

	/**
	 * @param {Response} http_response
	 * @return {HTTPError}
	 */
	static from_response(http_response) {
		return new HTTPError({
			status: http_response.status,
			type: 'api_error',
			detail: `Error from URL: ${http_response.url}; status: ${http_response.status_text}`
		});
	}
}

function response_time_metrics_middleware(app) {
	// Create a histogram metric for HTTP request duration
	const request_duration = {
		type: 'Histogram',
		name: `${app.conf.name}_express_router_request_duration_seconds`,
		help: 'request duration handled by router in seconds',
		buckets: [0.01, 0.05, 0.1, 0.3, 1],
		labels: {
			names: ['path', 'method', 'status']
		}
	};
	// Create the metric
	// This will return the existing metric if it already exists
	const response_time_metric = app.metrics.make_metric(request_duration);
	app.logger.info('response_time_metric', response_time_metric.labels);
	return (req, res, next) => {
		const start = process.hrtime();
		const original_end = res.end;

		res.end = (...args) => {
			// Calculate the duration
			const diff = process.hrtime(start);
			const duration = diff[0] + diff[1] / 1e9;

			const path = req.route ? req.route.path : req.path;
			// Observe the duration
			response_time_metric.observe(
				{
					method: req.method,
					path: path,
					status: res.status_code
				},
				duration
			);
			// Call the original end function
			original_end.apply(res, args);
		};
		// Continue processing the request
		next();
	};
}

function Deferred() {
	this.promise = new Promise(((resolve, reject) => {
		this.resolve = resolve;
		this.reject = reject;
	}));

	this.then = this.promise.then.bind(this.promise);
	this.catch = this.promise.catch.bind(this.promise);
}

/**
 * Check if the given content is plain text or contains html tags.
 * The check is performed by looking for open and close tags.
 * If the content has HTML entities, this test will not identify it.
 *
 * @param {string} content The content to test
 * @return {boolean} Return true if the content is plain text
 */
function is_plain_text(content) {
	return !content || !content.trim() || !/<[a-zA-Z][\s\S]*>/i.test(content);
}

/**
 * Null safe object getter
 * Example: To access obj.a.b.c[0].d in null safe way,
 * use get_prop(['a', 'b', 'c', 0, 'd'], obj )
 *
 * @param {string|number} path access path
 * @param {Object} obj Object
 * @return {Object|string|number|null}
 */
function get_prop(path, obj) {
	return path.reduce(
		(accumulator, current_value) => (accumulator && accumulator[current_value]) ?
			accumulator[current_value] :
			null,
		obj
	);
}

function get_config(conf_path) {
	if (!conf_path) {
		const dirname = new URL('.', import.meta.url).pathname;
		conf_path = `${dirname}/../config.dev.yaml`;
	}
	const config = load(readFileSync(conf_path));
	if (!config) {
		throw new Error('Failed to load config from path: ' + conf_path);
	}
	return config;
}

/**
 * Asserts that the language codes, if provided, are valid.
 *
 * @param {Response} res Response object
 * @param {...string} languages Language codes
 */
function assert_valid_language_codes(res, ...languages) {
	for (const language of languages) {
		if (language === undefined) {
			continue;
		}

		if (!language_data.is_known(language)) {
			res.status(400).end(`Invalid language code ${language}`);
			return false;
		}
	}

	return true;
}

export {
	HTTPError,
	get_config,
	response_time_metrics_middleware,
	get_prop,
	Deferred,
	is_plain_text,
	assert_valid_language_codes
};
