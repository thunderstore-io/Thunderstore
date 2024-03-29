const { src, dest, watch, parallel } = require("gulp");
const sass = require("gulp-sass");
const clean_css = require("gulp-clean-css");
const uglify = require("gulp-uglify");
const concat = require("gulp-concat");
const order = require("gulp-order");
const browserify = require("browserify");
const source = require("vinyl-source-stream");
const buffer = require("vinyl-buffer");
const tsify = require("tsify");
const merge = require("merge-stream");

function js(debug) {
    const vendorBuild = src([
        "node_modules/jquery/dist/jquery.js",
        "node_modules/popper.js/dist/umd/popper.js",
        "node_modules/bootstrap/dist/js/bootstrap.js",
        "node_modules/slim-select/dist/slimselect.js",
    ])
        .pipe(
            order(
                [
                    "node_modules/jquery/dist/jquery.js",
                    "node_modules/popper.js/dist/umd/popper.js",
                    "node_modules/bootstrap/dist/js/bootstrap.js",
                    "node_modules/slim-select/dist/slimselect.js",
                ],
                { base: "./" }
            )
        )
        .pipe(concat("vendor.js"));

    const tsBuild = browserify({
        basedir: ".",
        debug: debug,
        entries: ["src/main.ts"],
        cache: {},
        packageCache: {},
    })
        .plugin(tsify)
        .bundle()
        .on("error", (err) => console.log(err))
        .pipe(source("bundle.js"));

    let result = merge(vendorBuild, tsBuild)
        .pipe(buffer())
        .pipe(order(["vendor.js", "bundle.js"]))
        .pipe(concat("all.js"));
    if (!debug) {
        result = result.pipe(uglify());
    }
    return result.pipe(dest("./build/js/"));
}

function js_workers(debug) {
    // TODO: Iterate all source files in src/workers individually instead of
    //       just the md5 worker.
    let tsBuild = browserify({
        basedir: ".",
        debug: debug,
        entries: ["worker_src/md5.ts"],
        cache: {},
        packageCache: {},
    })
        .plugin(tsify)
        .bundle()
        .on("error", (err) => console.log(err))
        .pipe(source("md5.js"));

    let result = tsBuild.pipe(buffer()).pipe(concat("md5.js"));
    if (!debug) {
        result = result.pipe(uglify());
    }
    return result.pipe(dest("./build/js/workers/"));
}

function js_prod() {
    return js(false);
}

function js_debug() {
    return js(true);
}

function workers_prod() {
    return js_workers(false);
}

function workers_debug() {
    return js_workers(true);
}

function watch_js() {
    return watch(
        ["./src/**/*.ts", "./src/**/*.tsx", "./src/**/*.js"],
        { usePolling: true },
        js_debug
    );
}

function watch_workers() {
    return watch(
        [
            "./src/**/*.ts",
            "./src/**/*.tsx",
            "./src/**/*.js",
            "./worker_src/**/*.ts",
            "./worker_src/**/*.tsx",
            "./worker_src/**/*.js",
        ],
        { usePolling: true },
        workers_debug
    );
}

function css() {
    return src("src/scss/**/*.scss")
        .pipe(sass().on("error", sass.logError))
        .pipe(clean_css())
        .pipe(dest("./build/css/"));
}

function watch_css() {
    watch(
        ["./src/scss/**/*.scss", "./src/scss/**/*.css"],
        { usePolling: true },
        css
    );
}

exports.watch = parallel(
    js_debug,
    watch_js,
    workers_debug,
    watch_workers,
    css,
    watch_css
);
exports.default = parallel(js_prod, workers_prod, css);
