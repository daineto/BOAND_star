(define (problem p22) (:domain icylake)

(:objects 
upperwall-0 - wall upperwall-1 - wall upperwall-2 - wall upperwall-3 - wall upperwall-4 - wall upperwall-5 - wall
leftwall-5 - wall tile_0_5 - ice tile_1_5 - ice tile_2_5 - ice tile_3_5 - ice tile_4_5 - ice tile_5_5 - ice rightwall-5 - wall
leftwall-4 - wall tile_0_4 - ice tile_1_4 - pit tile_2_4 - ice tile_3_4 - ice tile_4_4 - ice tile_5_4 - pit rightwall-4 - wall
leftwall-3 - wall tile_0_3 - ice tile_1_3 - ice tile_2_3 - ice tile_3_3 - ice tile_4_3 - ice tile_5_3 - ice rightwall-3 - wall
leftwall-2 - wall tile_0_2 - ice tile_1_2 - ice tile_2_2 - ice tile_3_2 - ice tile_4_2 - ice tile_5_2 - ice rightwall-2 - wall
leftwall-1 - wall tile_0_1 - pit tile_1_1 - ice tile_2_1 - ice tile_3_1 - pit tile_4_1 - ice tile_5_1 - pit rightwall-1 - wall
leftwall-0 - wall tile_0_0 - ice tile_1_0 - ice tile_2_0 - wall tile_3_0 - ice tile_4_0 - ice tile_5_0 - ice rightwall-0 - wall
bottomwall-0 - wall bottomwall-1 - wall bottomwall-2 - wall bottomwall-3 - wall bottomwall-4 - wall bottomwall-5 - wall
)

(:init
(at tile_5_5)

(left-of leftwall-5 tile_0_5) (left-of tile_0_5 tile_1_5) (left-of tile_1_5 tile_2_5) (left-of tile_2_5 tile_3_5) (left-of tile_3_5 tile_4_5) (left-of tile_4_5 tile_5_5) (left-of tile_5_5 rightwall-5)
(left-of leftwall-4 tile_0_4) (left-of tile_0_4 tile_1_4) (left-of tile_1_4 tile_2_4) (left-of tile_2_4 tile_3_4) (left-of tile_3_4 tile_4_4) (left-of tile_4_4 tile_5_4) (left-of tile_5_4 rightwall-4)
(left-of leftwall-3 tile_0_3) (left-of tile_0_3 tile_1_3) (left-of tile_1_3 tile_2_3) (left-of tile_2_3 tile_3_3) (left-of tile_3_3 tile_4_3) (left-of tile_4_3 tile_5_3) (left-of tile_5_3 rightwall-3)
(left-of leftwall-2 tile_0_2) (left-of tile_0_2 tile_1_2) (left-of tile_1_2 tile_2_2) (left-of tile_2_2 tile_3_2) (left-of tile_3_2 tile_4_2) (left-of tile_4_2 tile_5_2) (left-of tile_5_2 rightwall-2)
(left-of leftwall-1 tile_0_1) (left-of tile_0_1 tile_1_1) (left-of tile_1_1 tile_2_1) (left-of tile_2_1 tile_3_1) (left-of tile_3_1 tile_4_1) (left-of tile_4_1 tile_5_1) (left-of tile_5_1 rightwall-1)
(left-of leftwall-0 tile_0_0) (left-of tile_0_0 tile_1_0) (left-of tile_1_0 tile_2_0) (left-of tile_2_0 tile_3_0) (left-of tile_3_0 tile_4_0) (left-of tile_4_0 tile_5_0) (left-of tile_5_0 rightwall-0)

(down-of tile_0_5 upperwall-0) (down-of tile_1_5 upperwall-1) (down-of tile_2_5 upperwall-2) (down-of tile_3_5 upperwall-3) (down-of tile_4_5 upperwall-4) (down-of tile_5_5 upperwall-5) 
(down-of tile_0_4 tile_0_5) (down-of tile_1_4 tile_1_5) (down-of tile_2_4 tile_2_5) (down-of tile_3_4 tile_3_5) (down-of tile_4_4 tile_4_5) (down-of tile_5_4 tile_5_5)
(down-of tile_0_3 tile_0_4) (down-of tile_1_3 tile_1_4) (down-of tile_2_3 tile_2_4) (down-of tile_3_3 tile_3_4) (down-of tile_4_3 tile_4_4) (down-of tile_5_3 tile_5_4)
(down-of tile_0_2 tile_0_3) (down-of tile_1_2 tile_1_3) (down-of tile_2_2 tile_2_3) (down-of tile_3_2 tile_3_3) (down-of tile_4_2 tile_4_3) (down-of tile_5_2 tile_5_3)
(down-of tile_0_1 tile_0_2) (down-of tile_1_1 tile_1_2) (down-of tile_2_1 tile_2_2) (down-of tile_3_1 tile_3_2) (down-of tile_4_1 tile_4_2) (down-of tile_5_1 tile_5_2)
(down-of tile_0_0 tile_0_1) (down-of tile_1_0 tile_1_1) (down-of tile_2_0 tile_2_1) (down-of tile_3_0 tile_3_1) (down-of tile_4_0 tile_4_1) (down-of tile_5_0 tile_5_1)
(down-of bottomwall-0 tile_0_0) (down-of bottomwall-1 tile_1_0) (down-of bottomwall-2 tile_2_0) (down-of bottomwall-3 tile_3_0) (down-of bottomwall-4 tile_4_0) (down-of bottomwall-5 tile_5_0))

(:goal
(and (at tile_5_0))
)
)