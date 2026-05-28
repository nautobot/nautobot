#! /bin/bash

# !!! IMPORTANT - READ THIS FIRST !!!
# This script is to be used ONLY when building PUBLIC documentation hosted
# on ReadTheDocs! It's executed in the pipeline defined in .readthedocs.yaml
# and inserts a Google Tag Manager tracking code for web analytics.
# Do NOT reuse this to insert analytics code in your development environments
# or into the release process (i.e. built packages).

cat > ./docs/assets/overrides/main.html <<EOL
{% extends "base.html" %}

{% block analytics %}
    <!-- Google Tag Manager -->
    <script>(function (w, d, s, l, i) {
            w[l] = w[l] || []; w[l].push({
                'gtm.start':
                    new Date().getTime(), event: 'gtm.js'
            }); var f = d.getElementsByTagName(s)[0],
                j = d.createElement(s), dl = l != 'dataLayer' ? '&l=' + l : ''; j.async = true; j.src =
                    'https://www.googletagmanager.com/gtm.js?id=' + i + dl; f.parentNode.insertBefore(j, f);
        })(window, document, 'script', 'dataLayer', 'GTM-K44D86GP');</script>
    <!-- End Google Tag Manager -->

{{ super() }}
{% endblock %}

{% block header %}
    <!-- Google Tag Manager (noscript) -->
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-K44D86GP" height="0" width="0"
            style="display:none;visibility:hidden"></iframe></noscript>
    <!-- End Google Tag Manager (noscript) -->

{{ super() }}
{% endblock %}
EOL
