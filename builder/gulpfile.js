const { src, dest, watch, parallel } = require("gulp");
const sass = require("gulp-sass");
const clean_css = require("gulp-clean-css");
const uglify = require("gulp-uglify");
const concat = require("gulp-concat");
const order = require("gulp-order");

function js() {
    return src("./src/js/**/*.js")
        .pipe(
            order(["vendor/jquery-3.3.1.min.js", "vendor/**/*.js", "**/*.js"])
        )
        .pipe(concat("all.js"))
        .pipe(uglify())
        .pipe(dest("./build/js/"));
}

function watch_js() {
    watch("./src/js/**/*.js", { usePolling: true }, js);
}

function css() {
    return src("./src/scss/**/*.scss")
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

exports.watch = parallel(js, watch_js, css, watch_css);
exports.default = parallel(js, css);
