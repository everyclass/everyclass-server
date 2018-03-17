var gulp = require('gulp'),
    gutil = require('gulp-util'),
    concat = require('gulp-concat'),           //Concat CSS files
    minifyCss = require('gulp-clean-css'),     //Compress CSS
    uglify = require('gulp-uglify'),           //JS uglify
    rename = require('gulp-rename'),           //File renaming
    rev = require('gulp-rev'),                 //File revision
    pump = require('pump');


//CSS task sets
//files are uglified and saved to `dist` then should be copied to `static` for local development
gulp.task('css', ['cssCompress', 'cssCopyToSrc']);

gulp.task('cssCompress', function () {
    gulp.src('./everyclass/static/css/*-v1.css')
    //.pipe(concat('style.min.css'))                 //Concat CSS files
        .pipe(minifyCss())                           //Compress
        .pipe(rev())                                 //Revision
        .pipe(gulp.dest('./dist/css'))                  //Output
        .pipe(rev.manifest())                        //Generate rev-manifest.json
        .pipe(gulp.dest('./everyclass'));            //Save rev-manifest.json for flask app
});

//this is for local dev. Looking for better solution.
gulp.task('cssCopyToSrc', ['cssCompress'], function () {
    gulp.src('./dist/css/*-*-*.css')
        .pipe(gulp.dest('./everyclass/static/css'));
});


//JS task sets
gulp.task('js', ['jsMinify', 'jsCopyToSrc']);

//use original js from src, uglify and save to `dist`
gulp.task('jsMinify', function (cb) {
    pump([
            gulp.src(['./everyclass/static/js/*.js', '!./everyclass/static/js/*.min.js', '!./everyclass/static/js/*_min.js']),
            uglify(),
            rename({suffix: '.min'}),
            gulp.dest('./dist/js')
        ],
        cb
    );
});

//copy javascript files from `dist` to `static`
gulp.task('jsCopyToSrc', ['jsMinify'], function () {
    gulp.src('./dist/js/*.min.js')
        .pipe(gulp.dest('./everyclass/static/js'));
});


//Main Task Sets
//run `gulp` to process both css and js
gulp.task('default', ['css', 'js']);


//Watch tasks
gulp.task('watch', function () {
    gulp.watch('./everyclass/static/css/*.css', ['css']);
    gulp.watch('./everyclass/static/js/*.js', ['js']);
});
//gulp.watch('./src/**/*',['rev']);
//gulp.watch('./src/everyclass/static/*.css',['rev']);


//Others
gulp.task('rev', ['cssConcat'], function () {
    console.log(111);
    gulp.src(['./rev/rev-manifest.json', './src/index.html'])   //- 读取 rev-manifest.json 文件以及需要进行css名替换的文件
        .pipe(revCollector())                                   //- 执行文件内css名的替换
        .pipe(gulp.dest('./build/'));                     //- 替换后的文件输出的目录
});

gulp.task('hello', function () {
    gutil.log("Message:" + gutil.colors.green('Hello!'))
});