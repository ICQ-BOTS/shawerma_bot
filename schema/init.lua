box.cfg {
    listen = 3301
}

box.schema.user.grant('guest', 'read,write,execute', 'universe', nil, { if_not_exists = true })
box.schema.user.passwd('pass')


function init()

--------------------------------Users--------------------------------

if box.space.statistics == nil then
	local statistics = box.schema.space.create('statistics', { if_not_exists = true })
	
	statistics:format({
		{ name = 'user_id', 	type = 'string' },
		{ name = 'count', 		type = 'integer' }
	})


	statistics:create_index('primary', { type = 'hash', parts = { 'user_id' }, if_not_exists = true, unique = true })
	
	--statistics:insert{'751509498', 2}
end


end

function reinit()
	reinitArray = { 
		--box.space.users, 
		--box.space.tests, 
		--box.sequence.tests_ids_autoinc, 
		--box.space.questions, 
		--box.sequence.questions_ids_autoinc, 
		--box.space.tests_results,
		--box.sequence.tests_results_ids_autoinc, 
		--box.space.answers,
		--box.sequence.answers_ids_autoinc,
		box.space.statistics
	}
	for key, value in pairs(reinitArray) do
		if value ~= nil then
			value:drop()
		end
	end
	
	
	init()
end

--reinit()

box.once("data", init)