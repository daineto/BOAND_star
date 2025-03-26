(define (problem fr_2_2)
    (:domain first-response)
    (:objects
        l1 l2 - location
        v1 v2 - victim
        m1 m2 - medical_unit
        ;m1 - medical_unit
    )
    (:init
        (hospital l1)
        (victim-at v1 l2)
        (victim-status v1 hurt)
        (victim-at v2 l1)
        (victim-status v2 hurt)
        (adjacent l1 l2)
        (adjacent l2 l1)
        (medical-unit-at m1 l2)
        (medical-unit-at m2 l1)
    )
    (:goal
        (and
            (victim-status v1 healthy)
            (victim-status v2 healthy)
        )
    )
)
