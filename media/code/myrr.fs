( myrr - custom text to html parser )
( Credit: Sean C. Lewis 2025, Samual A Falvo II 2008 )
( CC Share Alike: https://creativecommons.org/licenses/by-sa/4.0/deed.en )

( reading in a source file and outputting a destination file )
( data is code, we're writing an interpreter )
( html is by definition character based while Forth is word based )
  ( ! - store ... ( value address -- , STORE value TO address in memory )
  ( @ - fetch ... ( address -- value , FETCH value FROM address in memory ) 
  ( ? - look  ... ( address -- , look at variable )
  ( VARIABLE  ... ( <name> -- , define a 4 byte memory storage location )
warnings off

( configuration )
: srcfile	S" vindauga.mrr" ;
: outfile 	S" vindauga.html" ;

( input buffer )
VARIABLE 'src ( address )
VARIABLE #src ( size of buffer )
VARIABLE 'out
VARIABLE #out

VARIABLE fh

: open      srcfile R/O OPEN-FILE THROW fh ! ;
: close     fh @ CLOSE-FILE THROW ;
: read      BEGIN HERE 4096 fh @ READ-FILE THROW DUP ALLOT 0= UNTIL ;
: gulp 	    open read close ;
: start     HERE 'src ! ;
: finish    HERE 'src @ - #src ! ;
: slurp     start gulp finish ;
: open      outfile R/W CREATE-FILE THROW fh ! ;
: write     'out @ #out @ fh @ WRITE-FILE THROW ;
: spew 	    open write close ;

( command dispatcher)
variable offset
variable 'token
variable #token

: addr      offset @ 'src @ + ;
: chr 	    addr C@ ;
: -ws 	    32 U> ;
: advance   1 offset +! ;
: seek 	    begin chr -ws WHILE advance REPEAT ;
: token     addr seek addr over - advance 2DUP #token ! 'token ! ;
: .token    'token @ #token @ TYPE ;
: error     CR CR .token -1 ABORT" Command was not found" ;
: command   token sfind IF EXECUTE ELSE error THEN ;

( vectored output )

: b-emit	C, ;
: b-type	BEGIN DUP WHILE OVER C@ EMIT 1 /string REPEAT 2DROP ;
: buffered	['] b-emit IS EMIT ['] b-type IS TYPE ;
: interactive	['] (EMIT) IS EMIT ['] (TYPE) IS TYPE ;
: start		HERE 'out ! buffered ;
: finish 	HERE 'out @ - #out ! interactive ; 

( process input buffer )

: rdrop     POSTPONE R> POSTPONE DROP ; IMMEDIATE
: call 	    >R ;
: entity    [CHAR] & emit type [CHAR] ; emit ;
: ===> 	    OVER = IF DROP R> call entity THEN rdrop ; ( custom syntax; most benefits of polymorphism )
: either&   [CHAR] & ===> S" amp" ; ( mapping symbols to entities )
: or<	    [CHAR] < ===> S" lt" ;
: or>	    [CHAR] > ===> S" gt" ;
: orESC     DUP [CHAR] ~ = IF DROP command RDROP EXIT THEN ;
: interpret chr advance either& or< or> orEsc ( else ) emit ;
: -end 	    offset @ #src @ U< ;
: format    0 offset ! BEGIN -end WHILE interpret REPEAT ;
: process   start format finish ;

( commands )
: html	    ." <!DOCTYPE html><head><title>" outfile TYPE ." </title></head><body>" CR ;
: /html     ." </body></html>" ;
: style     ." <style> body { padding: 30px; text-align: absolute center; } </style>" CR ;
: p	    ." <p>" ;
: /p	    ." </p>" ;
: +p	    /p CR p ;
: h2	    ." <h2>" ;
: /h2	    ." </h2>" ;
: code      ." <code>" ;
: /code	    ." </code> " ;
: ul  	    ." <ul>" CR ;
: /ul	    ." </ul>" CR ;
: li	    ." <li>" ;
: /li	    ." </li>" CR ;
: +li	    /li CR li ;
: img	    ." <figure><img src='" token TYPE ." 'style='width:250px;'/></figure>" ;
: iw	    ." <i>" token TYPE ." </i> " ;
: bw        ." <b>" token TYPE ." </b> " ;
: cw	    ." <code>" token TYPE ." </code> " ;
: href	    ." <a href=" token TYPE ." >" ;
: /href	    ." </a> " ;
: pre	    ." <blockquote><pre>" ;
: /pre	    ." </pre></blockquote> " ;

( kick off procedures )
: myrr      slurp process spew ;
myrr BYE
