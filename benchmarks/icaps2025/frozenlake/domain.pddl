;Header and description

(define (domain icylake)

;remove requirements that are not needed
(:requirements :strips :typing :non-deterministic)

(:types 
    tile - object
    ice wall pit - tile
)

(:predicates ;todo: define predicates here
    (at ?tile - tile)
    (left-of ?left - tile ?right - tile)
    (down-of ?down - tile ?up - tile)
)

;define actions here

(:action left
    :parameters (?src - ice ?dst1 - ice ?dst2 - ice)
    :precondition (and (at ?src) (left-of ?dst1 ?src) (left-of ?dst2 ?dst1))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?dst2))
     )
)

(:action left-to-wall
    :parameters (?src - ice ?dst1 - ice ?w - wall)
    :precondition (and (at ?src) (left-of ?dst1 ?src) (left-of ?w ?dst1))
    :effect (and
        (not (at ?src)) (at ?dst1)
     )
)

(:action left-to-pit
    :parameters (?src - ice ?dst1 - ice ?p - pit)
    :precondition (and (at ?src) (left-of ?dst1 ?src) (left-of ?p ?dst1))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?p))
     )
)

(:action right
    :parameters (?src - ice ?dst1 - ice ?dst2 - ice)
    :precondition (and (at ?src) (left-of ?src ?dst1) (left-of ?dst1 ?dst2))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?dst2))
     )
)

(:action right-to-wall
    :parameters (?src - ice ?dst1 - ice ?w - wall)
    :precondition (and (at ?src) (left-of ?src ?dst1) (left-of ?dst1 ?w))
    :effect (and
        (not (at ?src)) (at ?dst1)
     )
)

(:action right-to-pit
    :parameters (?src - ice ?dst1 - ice ?p - pit)
    :precondition (and (at ?src) (left-of ?src ?dst1) (left-of ?dst1 ?p))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?p))
     )
)

(:action down
    :parameters (?src - ice ?dst1 - ice ?dst2 - ice)
    :precondition (and (at ?src) (down-of ?dst1 ?src) (down-of ?dst2 ?dst1))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?dst2))
     )
)

(:action down-to-wall
    :parameters (?src - ice ?dst1 - ice ?w - wall)
    :precondition (and (at ?src) (down-of ?dst1 ?src) (down-of ?w ?dst1))
    :effect (and
        (not (at ?src)) (at ?dst1)
     )
)

(:action down-to-pit
    :parameters (?src - ice ?dst1 - ice ?p - pit)
    :precondition (and (at ?src) (down-of ?dst1 ?src) (down-of ?p ?dst1))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?p))
     )
)

(:action up
    :parameters (?src - ice ?dst1 - ice ?dst2 - ice)
    :precondition (and (at ?src) (down-of ?src ?dst1) (down-of ?dst1 ?dst2))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?dst2))
     )
)

(:action up-to-wall
    :parameters (?src - ice ?dst1 - ice ?w - wall)
    :precondition (and (at ?src) (down-of ?src ?dst1) (down-of ?dst1 ?w))
    :effect (and
        (not (at ?src)) (at ?dst1)
     )
)

(:action up-to-pit
    :parameters (?src - ice ?dst1 - ice ?p - pit)
    :precondition (and (at ?src) (down-of ?src ?dst1) (down-of ?dst1 ?p))
    :effect (and
        (not (at ?src))
        (oneof (at ?dst1) (at ?p))
     )
)


)