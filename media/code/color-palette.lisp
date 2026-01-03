(open $path)

(def unit 40) ; Size and placement of circles
(def f
  (get-frame))

; For aesthetically spaced rows
;(def posy-row-1
;  (sub f:h
;    (mul unit 4)))

; Flush rows
(def posy-row-1
  (sub f:h
    (mul unit (add 2 (sqrt 3)))))
(def posy-row-2
  (sub f:h
    (mul unit 2)))

(def color-1
  (pick
    (guide
      $rect)))
(def color-2
  (pick
    (guide
      $rect)))
(def color-3
  (pick
    (guide
      $rect)))
(def color-4
  (pick
    (guide
      $rect)))
(def color-5
  (pick
    (guide
      $rect)))
(def color-6
  (pick
    (guide
      $rect)))
(def color-7
  (pick
    (guide
      $rect)))
(def color-8
  (pick
    (guide
      $rect)))

(fill
  (circle 
    (mul unit 2) posy-row-1 unit) color-1)
(fill
  (circle 
    (mul unit 4) posy-row-1 unit) color-2)
(fill
  (circle 
    (mul unit 6) posy-row-1 unit) color-3)
(fill
  (circle
    (mul unit 8) posy-row-1 unit) color-4)
(fill
  (circle
    (mul unit 3) posy-row-2 unit) color-5)
(fill
  (circle
    (mul unit 5) posy-row-2 unit) color-6)
(fill
  (circle
    (mul unit 7) posy-row-2 unit) color-7)
(fill
  (circle
    (mul unit 9) posy-row-2 unit) color-8)
