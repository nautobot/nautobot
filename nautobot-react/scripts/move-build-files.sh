#!/bin/sh

## FOR PROTOTYPE PURPOSES ONLY DO NOT USE IN PRODUCTION

STATIC_DIR=../nautobot/project-static
CSS_DIR=$STATIC_DIR/reactcss/core
JS_DIR=$STATIC_DIR/reactjs/core

if [ -d $CSS_DIR ]; then
    rm $CSS_DIR/*.css 2>/dev/null
else
    mkdir -p $CSS_DIR
fi

cp ./build/static/reactcss/core/*.css $CSS_DIR/

if [ -d $JS_DIR ]; then
    rm $JS_DIR/*.js 2>/dev/null
else
    mkdir -p $JS_DIR
fi

cp ./build/static/reactjs/core/*.js $JS_DIR/

cp ./build/index.html ../nautobot/core/templates/index_js.html
