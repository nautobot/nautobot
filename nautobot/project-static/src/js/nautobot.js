import '../scss/nautobot.scss';

import * as bootstrap from 'bootstrap';

import ClipboardJS from 'clipboard';
window.ClipboardJS = ClipboardJS;

import flatpickr from 'flatpickr';
window.flatpickr = flatpickr;

import hljs from 'highlight.js/lib/core';
import 'highlight.js/styles/github.css';
import graphql from 'highlight.js/lib/languages/graphql';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import yaml from 'highlight.js/lib/languages/yaml';
hljs.registerLanguage('graphql', graphql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('yaml', yaml);
window.hljs = hljs;

window.jQuery = require('jquery');
window.$ = window.jQuery;

import 'jquery-ui';
import 'select2';

