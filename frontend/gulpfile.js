var gulp = require('gulp'),
    gutil = require('gulp-util'),
    concat = require('gulp-concat'),           //Concat CSS files
    minifyCss = require('gulp-clean-css'),     //Compress CSS
    uglify = require('gulp-uglify'),           //JS uglify
    rename = require('gulp-rename'),           //File renaming
    rev = require('gulp-rev'),                 //File revision
    pump = require('pump');


//CSS
gulp.task('css', ['cssCompress']);
gulp.task('cssCompress', function () {
    gulp.src("./static/css/*-v1.css")
    //.pipe(concat('style.min.css'))                 //Concat CSS files
        .pipe(minifyCss())                           //Compress
        .pipe(rev())                                 //Revision
        .pipe(gulp.dest('./dist/css'))               //Output
        .pipe(rev.manifest())                        //Generate rev-manifest.json
        .pipe(gulp.dest('./'));                      //Save rev-manifest.json
});


//JS
gulp.task("js", ["jsMinify"]);
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


// 把 static 目录的其他文件拷贝到 dist 目录
gulp.task('copyOtherFilesToDist', function () {
    gulp.src(['./static', '!./static/css', '!./static/js'])
        .pipe(gulp.dest('./dist'));
});


// 默认任务
// 运行 `gulp` 命令压缩 CSS、JS，并生成完整的 dist 目录
gulp.task("default", ["css", "js", "copyOtherFilesToDist"]);


//Watch tasks
gulp.task('watch', function () {
    gulp.watch('./static/css/*.css', ['css']);
    gulp.watch('./static/js/*.js', ['js']);
});
//gulp.watch('./src/**/*',['rev']);
//gulp.watch('./src/everyclass/static/*.css',['rev']);


//Others
gulp.task('rev', ['cssConcat'], function () {
    console.log(111);
    gulp.src(['./rev-manifest.json'])   //- 读取 rev-manifest.json 文件
        .pipe(revCollector())           //- 执行文件内css名的替换
        .pipe(gulp.dest('./build/'));   //- 替换后的文件输出的目录
});

gulp.task("hello", function () {
    gutil.log("Message:" + gutil.colors.green('Hello!'))
});