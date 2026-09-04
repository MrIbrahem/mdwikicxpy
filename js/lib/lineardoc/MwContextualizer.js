import Contextualizer from './Contextualizer.js';
import { get_prop } from './../util.js';
const content_branch_node_names = ['blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'div', 'table', 'ol', 'ul', 'dl', 'figure', 'center', 'section'];

/**
 * Contextualizer for Media_wiki DOM HTML
 *
 * See https://www.mediawiki.org/wiki/Specs/HTML
 *
 * @class
 * @extends Contextualizer
 * @constructor
 */
class Mw_contextualizer extends Contextualizer {
	/**
	 * @param {Object} config
	 * @param {Object} config.removable_sections containing array of classes and rdfa values.
	 *  Tags matching these classes or rdfa values will be marked as removable.
	 *  See config/MWPage_loader.yaml
	 */
	constructor(config) {
		super(config);
		// Array holding transclusion fragment ids(about attribute values)
		this.removable_transclusion_fragments = [];
	}

	/**
	 * @inheritdoc
	 */
	get_child_context(tag) {
		const context = this.get_context(),
			type = tag.attributes.typeof || tag.attributes.rel || '';

		if (context === 'removable' || this.is_removable(tag)) {
			return 'removable';
		}

		// Any descendent of Transclusion/Placeholder is verbatim
		if (context === 'verbatim' || type.match(/(^|\s)(mw:Transclusion|mw:Placeholder)\b/)) {
			return 'verbatim';
		}

		// Otherwise, figure is media
		if (tag.name === 'figure') {
			return 'media';
		}

		if (tag.name === 'span' && type.match(/(^|\s)(mw:File|mw:Image|mw:Video|mw:Audio)\b/)) {
			return 'media-inline';
		}

		// Immediate childrens of body are sections
		if (context === undefined && tag.name === 'body') {
			return 'section';
		}

		// And figure//figcaption is content_branch
		if ((context === 'media' || context === 'media-inline') && tag.name === 'figcaption') {
			return 'content_branch';
		}

		// And Content_branch_nodes are content_branch
		if ((context === 'section' || context === undefined) && content_branch_node_names.includes(tag.name)) {
			return 'content_branch';
		}

		// Else same as parent context
		return context;
	}

	/**
	 * @inheritdoc
	 */
	can_segment() {
		return this.get_context() === 'content_branch';
	}

	/**
	 * Check if the tag need to be ignored while parsing and hence removed.
	 *
	 * @param {Object} tag
	 * @return {boolean}
	 */
	is_removable(tag) {
		const removable_sections = this.config.removable_sections;
		if (!this.config.removable_sections) {
			return false;
		}

		if (this.removable_transclusion_fragments.includes(tag.attributes.about)) {
			// Once a transclusion is removed, make sure their fragments also removed
			// even if the fragment does not match with removable_sections configuration.
			return true;
		}

		const class_list = tag.attributes.class ? tag.attributes.class.split(' ') : [];
		for (let i = 0; i < removable_sections.classes.length; i++) {
			if (class_list.includes(removable_sections.classes[i])) {
				if (tag.attributes.about) {
					this.removable_transclusion_fragments.push(tag.attributes.about);
				}
				return true;
			}
		}

		const types = tag.attributes.typeof ? tag.attributes.typeof.split(' ') : [];
		const rels = tag.attributes.rel ? tag.attributes.rel.split(' ') : [];
		const rdfa = types.concat(rels);
		for (let i = 0; i < removable_sections.rdfa.length; i++) {
			// Make sure that the rdfa value matches with removable section rdfa and does not
			// have other rdfas in same element.
			if (rdfa.includes(removable_sections.rdfa[i] && rdfa.length === 1)) {
				if (tag.attributes.about) {
					this.removable_transclusion_fragments.push(tag.attributes.about);
				}
				return true;
			}
		}

		const dataMW = tag.attributes['data-mw'];
		if (!dataMW) {
			return false;
		}

		// See https://phabricator.wikimedia.org/T274133 for more info
		let mw_data = {};
		try {
			mw_data = JSON.parse(dataMW);
		} catch (e) {
			return false;
		}
		const template_name = get_prop(['parts', 0, 'template', 'target', 'wt'], mw_data);
		if (!template_name) {
			return false;
		}

		for (let i = 0; i < removable_sections.templates.length; i++) {
			let removable_template_name_reg_exp;
			const removable_template_name = removable_sections.templates[i];

			if (removable_template_name[0] === '/' && removable_template_name.slice(-1) === '/') {
				// A regular expression is given.
				removable_template_name_reg_exp = new Reg_exp(removable_template_name.slice(1, -1), 'i');
			}

			const match = removable_template_name_reg_exp ?
				template_name.match(removable_template_name_reg_exp) :
				template_name.to_lower_case() === removable_template_name.to_lower_case();

			if (match) {
				if (tag.attributes.about) {
					this.removable_transclusion_fragments.push(tag.attributes.about);
				}
				return true;
			}
		}

		return false;
	}
}

export default Mw_contextualizer;
