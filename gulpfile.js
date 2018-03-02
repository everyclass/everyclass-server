var gulp = require('gulp');
var gutil = require('gulp-util');
var concat = require('gulp-concat');                            //Concat CSS files
var minifyCss = require('gulp-clean-css');                      //Compress CSS
var uglify = require('gulp-uglify');
var rev = require('gulp-rev');                                  //File revision


//CSS
//css files are uglified and saved to `dist` then should be copied to `static` for local development
gulp.task('css', ['cssCompress', 'cssCopyToSrc']);

gulp.task('cssCompress', function () {
    gulp.src('./everyclass/static/*-v1.css')
    //.pipe(concat('style.min.css'))                        //Concat CSS files
        .pipe(minifyCss())                                      //Compress
        .pipe(rev())                                            //Revision
        .pipe(gulp.dest('./dist/'))                             //Output
        .pipe(rev.manifest())                                   //Generate rev-manifest.json
        .pipe(gulp.dest('./everyclass'));                   //Save rev-manifest.json for flask app
});

gulp.task('cssCopyToSrc', function () {
    gulp.src('./dist/*-*-*.css')
        .pipe(gulp.dest('./everyclass/static'));
});


//JS
// javascript files is
gulp.task('js', ['jsMinify', 'jsCopyToDist']);

gulp.task('jsMinify', function () {
    gulp.src(['./everyclass/static/*.js', '!./everyclass/static/*.min.js'])
        .pipe(uglify())
        .pipe(gulp.dist('./dist/'))
});
gulp.task('jsCopyToDist', function () {
    gulp.src('./everyclass/static/*.min.js')
        .pipe(gulp.dest('./dist'));
});


//Task Sets
gulp.task('default', ['css', 'js']);


//Watch tasks
gulp.task('watch-css', function () {
    gulp.watch('./everyclass/static/*.css', ['cssCompile']);
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