var gulp = require('gulp'),
    concat = require('gulp-concat'),           //Concat CSS files
    minifyCss = require('gulp-clean-css'),     //Compress CSS
    uglify = require('gulp-uglify'),           //JS uglify
    rename = require('gulp-rename'),           //File renaming
    rev = require('gulp-rev'),                 //File revision
    pump = require('pump');


//CSS
gulp.task('cssCompress', function () {
    gulp.src("./static/css/*-v1.css")
    //.pipe(concat('style.min.css'))                 //Concat CSS files
        .pipe(minifyCss())                           //Compress
        .pipe(rev())                                 //Revision
        .pipe(gulp.dest('./dist/css'))               //Output
        .pipe(rev.manifest())                        //Generate rev-manifest.json
        .pipe(gulp.dest('./'));                      //Save rev-manifest.json
});
gulp.task('css', gulp.series('cssCompress'));

//JS
gulp.task('jsMinify', function (cb) {
    pump([
            gulp.src(['./static/js/*.js', '!./static/js/*.min.js', '!./static/js/*_min.js']),
            uglify(),
            rename({suffix: '.min'}),
            gulp.dest('./dist/js')
        ],
        cb
    );
});
gulp.task("js", gulp.series('jsMinify'));


// 把 static 目录的其他文件拷贝到 dist 目录
gulp.task('copyOtherFilesToDist', function () {
    gulp.src(['./static', '!./static/css', '!./static/js'])
        .pipe(gulp.dest('./dist'));
});


// 默认任务
// 运行 `gulp` 命令压缩 CSS、JS，并生成完整的 dist 目录
gulp.task("default", gulp.series("css", "js", "copyOtherFilesToDist"));


//Watch tasks
gulp.task('watch', function () {
    gulp.watch('./static/css/*.css', ['css']);
    gulp.watch('./static/js/*.js', ['js']);
});