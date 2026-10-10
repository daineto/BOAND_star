(define (domain first-response)
 (:requirements :non-deterministic :negative-preconditions :equality :typing)
 (:types location victim status medical_unit)
 (:constants healthy hurt dying - status)
 (:predicates 
  (victim-at ?v - victim ?l - location)
  (victim-status ?v - victim ?s - status)
  (hospital ?l - location)
  (adjacent ?l1 ?l2 - location)
  (medical-unit-at ?u - medical_unit ?l - location)
  (have-victim-in-unit ?v - victim ?u - medical_unit)
  )

 (:action drive-medical-unit
  :parameters (?u - medical_unit ?from - location ?to - location)
  :precondition (and (medical-unit-at ?u ?from)
		     (adjacent ?to ?from)
		     )
  :effect (and (medical-unit-at ?u ?to) (not (medical-unit-at ?u ?from)))
  )

 (:action load-victim
  :parameters (?u - medical_unit ?l - location ?v - victim)
  :precondition (and (medical-unit-at ?u ?l) (victim-at ?v ?l))
  :effect (and (have-victim-in-unit ?v ?u) 
	       (not (victim-at ?v ?l))))

 (:action unload-victim
  :parameters (?u - medical_unit ?l - location ?v - victim)
  :precondition (and (medical-unit-at ?u ?l)(have-victim-in-unit ?v ?u))
  :effect (and (victim-at ?v ?l) (not (have-victim-in-unit ?v ?u))))


 (:action treat-victim-on-scene
  :parameters (?u - medical_unit ?l - location ?v - victim)
  :precondition (and (medical-unit-at ?u ?l) 
		     (victim-at ?v ?l)
		     (victim-status ?v hurt))
  :effect (and (oneof (victim-status ?v healthy) (victim-status ?v dying)) (not (victim-status ?v hurt)))
 )

(:action reanimate
  :parameters (?u - medical_unit ?l - location ?v - victim)
  :precondition (and (medical-unit-at ?u ?l) 
		     (victim-at ?v ?l)
		     (victim-status ?v dying))
  :effect (and (not (victim-status ?v dying)) (victim-status ?v hurt))
 )

 (:action treat-victim-at-hospital
  :parameters (?v - victim ?l - location)
  :precondition (and (victim-at ?v ?l)
		     (hospital ?l))		     
  :effect (and (victim-status ?v healthy) 
	       (not (victim-status ?v hurt))
	       (not (victim-status ?v dying))))
  
)
