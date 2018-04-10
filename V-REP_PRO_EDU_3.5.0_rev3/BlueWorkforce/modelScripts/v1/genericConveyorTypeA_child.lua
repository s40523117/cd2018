function getTriggerType()
    if stopTriggerSensor~=-1 then
        local data=sim.readCustomDataBlock(stopTriggerSensor,simBWF.BINARYSENSOR_TAG)
        if data then
            data=sim.unpackTable(data)
            local state=data['detectionState']
            if not lastStopTriggerState then
                lastStopTriggerState=state
            end
            if lastStopTriggerState~=state then
                lastStopTriggerState=state
                return -1 -- means stop
            end
        end
    end
    if startTriggerSensor~=-1 then
        local data=sim.readCustomDataBlock(startTriggerSensor,simBWF.BINARYSENSOR_TAG)
        if data then
            data=sim.unpackTable(data)
            local state=data['detectionState']
            if not lastStartTriggerState then
                lastStartTriggerState=state
            end
            if lastStartTriggerState~=state then
                lastStartTriggerState=state
                return 1 -- means restart
            end
        end
    end
    return 0
end

function overrideMasterMotionIfApplicable(override)
    if masterConveyor>=0 then
        local data=sim.readCustomDataBlock(masterConveyor,simBWF.CONVEYOR_TAG)
        if data then
            data=sim.unpackTable(data)
            local stopRequests=data['stopRequests']
            if override then
                stopRequests[model]=true
            else
                stopRequests[model]=nil
            end
            data['stopRequests']=stopRequests
            sim.writeCustomDataBlock(masterConveyor,simBWF.CONVEYOR_TAG,sim.packTable(data))
        end
    end
end

function getMasterDeltaShiftIfApplicable()
    if masterConveyor>=0 then
        local data=sim.readCustomDataBlock(masterConveyor,simBWF.CONVEYOR_TAG)
        if data then
            data=sim.unpackTable(data)
            local totalShift=data['encoderDistance']
            local retVal=totalShift
            if previousMasterTotalShift then
                retVal=totalShift-previousMasterTotalShift
            end
            previousMasterTotalShift=totalShift
            return retVal
        end
    end
end

function sysCall_init()
    bwfPluginLoaded=sim.isPluginLoaded('Bwf')
    model=sim.getObjectAssociatedWithScript(sim.handle_self)
    local data=sim.readCustomDataBlock(model,simBWF.CONVEYOR_TAG)
    data=sim.unpackTable(data)
    stopTriggerSensor=simBWF.getReferencedObjectHandle(model,simBWF.CONVEYOR_STOP_SIGNAL_REF)
    startTriggerSensor=simBWF.getReferencedObjectHandle(model,simBWF.CONVEYOR_START_SIGNAL_REF)
    masterConveyor=simBWF.getReferencedObjectHandle(model,simBWF.CONVEYOR_MASTER_CONVEYOR_REF)
    getTriggerType()
    length=data['length']
    height=data['height']
    local err=sim.getInt32Parameter(sim.intparam_error_report_mode)
    sim.setInt32Parameter(sim.intparam_error_report_mode,0) -- do not report errors
    textureB=sim.getObjectHandle('genericConveyorTypeA_textureB')
    textureC=sim.getObjectHandle('genericConveyorTypeA_textureC')
    jointB=sim.getObjectHandle('genericConveyorTypeA_jointB')
    jointC=sim.getObjectHandle('genericConveyorTypeA_jointC')
    sim.setInt32Parameter(sim.intparam_error_report_mode,err) -- report errors again
    textureA=sim.getObjectHandle('genericConveyorTypeA_textureA')
    forwarderA=sim.getObjectHandle('genericConveyorTypeA_forwarderA')
    lastT=sim.getSimulationTime()
    beltVelocity=0
    totShift=0
    online=simBWF.isSystemOnline()
    if online then
        if bwfPluginLoaded then
            local data={}
            data.id=model
            simBWF.query('conveyor_getState',data) -- just to reset from last call
        end
    end
end 

function sysCall_actuation()
    local t=sim.getSimulationTime()
    local dt=t-lastT
    lastT=t
    local data=sim.readCustomDataBlock(model,simBWF.CONVEYOR_TAG)
    data=sim.unpackTable(data)
    if online then
        local ds=0
        if bwfPluginLoaded then
            local data={}
            data.id=model
            
            local res,retData=simBWF.query('conveyor_getState',data)
            if res=='ok' then
                ds=retData.displacement
            else
                if simBWF.isInTestMode() then
                    ds=0.001
                end
            end
        end
        totShift=totShift+ds
    else
        maxVel=data['velocity']
        accel=data['acceleration']
        enabled=sim.boolAnd32(data['bitCoded'],64)>0
        if not enabled then
            maxVel=0
        end
        local stopRequests=data['stopRequests']
        local trigger=getTriggerType()
        if trigger>0 then
            stopRequests[model]=nil -- restart
        end
        if trigger<0 then
            stopRequests[model]=true -- stop
        end
        if next(stopRequests) then
            maxVel=0
            overrideMasterMotionIfApplicable(true)
        else
            overrideMasterMotionIfApplicable(false)
        end

        local masterDeltaShift=getMasterDeltaShiftIfApplicable()
        if masterDeltaShift then
            totShift=totShift+masterDeltaShift
            beltVelocity=masterDeltaShift/dt
        else
            local dv=maxVel-beltVelocity
            if math.abs(dv)>accel*dt then
                beltVelocity=beltVelocity+accel*dt*math.abs(dv)/dv
            else
                beltVelocity=maxVel
            end
            totShift=totShift+dt*beltVelocity
        end


        if bwfPluginLoaded then
            local data={}
            data.id=model
            data.displacement=totShift
            
            simBWF.query('conveyor_state',data)
        end
    end
    local beltVelocity=0
    if previousTotShift then
        beltVelocity=(totShift-previousTotShift)/dt
    end
    sim.setObjectFloatParameter(textureA,sim.shapefloatparam_texture_y,totShift)

    if textureB~=-1 then
        sim.setObjectFloatParameter(textureB,sim.shapefloatparam_texture_y,length*0.5+0.041574*height/0.2+totShift)
        sim.setObjectFloatParameter(textureC,sim.shapefloatparam_texture_y,-length*0.5-0.041574*height/0.2+totShift)
        local a=sim.getJointPosition(jointB)
        sim.setJointPosition(jointB,a-beltVelocity*dt*2/height)
        sim.setJointPosition(jointC,a-beltVelocity*dt*2/height)
    end
    
    relativeLinearVelocity={0,beltVelocity,0}
    
    sim.resetDynamicObject(forwarderA)
    m=sim.getObjectMatrix(forwarderA,-1)
    m[4]=0
    m[8]=0
    m[12]=0
    absoluteLinearVelocity=sim.multiplyVector(m,relativeLinearVelocity)
    sim.setObjectFloatParameter(forwarderA,sim.shapefloatparam_init_velocity_x,absoluteLinearVelocity[1])
    sim.setObjectFloatParameter(forwarderA,sim.shapefloatparam_init_velocity_y,absoluteLinearVelocity[2])
    sim.setObjectFloatParameter(forwarderA,sim.shapefloatparam_init_velocity_z,absoluteLinearVelocity[3])
    data['encoderDistance']=totShift
    previousTotShift=totShift

    sim.writeCustomDataBlock(model,simBWF.CONVEYOR_TAG,sim.packTable(data))
end

