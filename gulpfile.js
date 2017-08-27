var gulp = require('gulp');
var gutil = require('gulp-util');
var concat = require('gulp-concat');                            //- 多个文件合并为一个；
var minifyCss = require('gulp-clean-css');                     //- 压缩CSS为一行；gulp-minify-css已经废弃
var rev = require('gulp-rev');                                  //- 对文件名加MD5后缀

gulp.task('hello', function () {
    gutil.log("Message:" + gutil.colors.green('Hello!'))
});

gulp.task('css', function() {                                //- 创建一个名为 css 的 task
    gulp.src('./src/everyclass/static/*.css')                    //- 需要处理的css文件，放到一个字符串数组里
        //.pipe(concat('style.min.css'))                            //- 合并后的文件名
        .pipe(minifyCss())                                      //- 压缩处理成一行
        .pipe(rev())                                            //- 文件名加MD5后缀
        .pipe(gulp.dest('./dist/'))                               //- 输出文件本地
        .pipe(rev.manifest())                                   //- 生成一个rev-manifest.json
        .pipe(gulp.dest('./src/everyclass'));                    //- 将 rev-manifest.json 保存到 rev 目录内
});

gulp.task('copyCSStoSrc',function(){
    gulp.src('./dist/*')
        .pipe(gulp.dest('./src/everyclass/static'));
});

gulp.task('rev',['cssConcat'],function() {console.log(111)
    gulp.src(['./rev/rev-manifest.json', './src/index.html'])   //- 读取 rev-manifest.json 文件以及需要进行css名替换的文件
        .pipe(revCollector())                                   //- 执行文件内css名的替换
        .pipe(gulp.dest('./build/'));                     //- 替换后的文件输出的目录
});
//gulp.watch('./src/**/*',['rev']);
//gulp.watch('./src/everyclass/static/*.css',['rev']);
gulp.task('default', ['hello', 'css']);