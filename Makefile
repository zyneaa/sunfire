user:
	python3 -m generators.user_gen

property:
	python3 -m generators.property_gen

score:
	python3 -m generators.score

simulate:
	python3 -m generators.property_gen
	python3 -m generators.user_gen
	python3 -m generators.score
