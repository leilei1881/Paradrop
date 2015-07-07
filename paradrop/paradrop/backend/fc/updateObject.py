
'''
updateObject module.

This holds onto the UpdateObject class.
It allows us to easily abstract away different update types and provide a uniform
way to interpret the results through a set of basic actionable functions.
'''

from paradrop.backend import exc
from paradrop.backend.fc import chutestorage
from paradrop.lib import settings

class UpdateObject(object):
    """
    The base UpdateObject class, covers a few basic methods but otherwise all the intelligence
    exists in the inherited classes.
    
    All update information passed by the API server is contained as variables of this class
    such as update.updateType, update.updateClass, etc...

    By default, the following variables should be utilized:
        responses : an array of messages any module can choose to append warnings or errors to
        
        failure   : the module that chose to fail this update can set a string message to return
                  : to the user in the failure variable. It should be very clear as to why the
                  : failure occurred, but if the user wants more information they may find it
                  : in the responses variable which may contain debug information, etc...
    """
    updateModuleList = []
    
    def __init__(self, obj):
        # Pull in all the keys from the obj identified
        self.__dict__.update(obj)
        self.responses = []
        self.failure = None
        # Use a temporary planmap for each chute
        self.plans = exc.plangraph.PlanMap(self.name)
        self.chuteStor = chutestorage.ChuteStorage()
    
    def __str__(self):
        return "<Update({}) :: {} - {} @ {}>".format(self.updateClass, self.name, self.updateType, self.tok)
    
    def __repr__(self):
        return "<Update({}) :: {}>".format(self.updateClass, self.name)

    def complete(self, **kwargs):
        """
            Signal to the API server that any action we need to perform is complete and the API 
            server can finish its connection with the client that initiated the API request.
        """
        if(settings.DEBUG_MODE):
            kwargs['responses'] = self.responses
        
        # Set our results
        self.result = kwargs
        
        # Call the function we were provided
        self.func(self)
    
    def execute(self):
        """
        The function that actually walks through the main process required to create the chute.
        It follows the executeplan module through the paces of:
            1) Generate the plans for each exc module
            2) Prioritize the plans
            3) Execute the plans
        
        If at any point we fail then this function will directly take care of completing
        the update process with an error state and will close the API connection.
        """
        # Generate the plans we need to setup the chute
        if(exc.executionplan.generatePlans(self)):
            out.warn('** %s Failed to generate plans\n' % logPrefix())
            self.complete(success=False, message=self.failure)
            return
        
        # Aggregate those plans
        exc.executionplan.aggregatePlans(self)

        # Execute on those plans
        # TODO

        # Now save the new state if we are all ok

        # Respond to the API server to let them know the result
        self.complete(success=True, message='Chute {} {} success'.format(
            self.name, self.updateType))

class UpdateChute(UpdateObject):
    """
    Updates specifically tailored to chute actions like create, delete, etc...
    """
    
    updateModuleList = [
        exc.name,
        exc.state,
        exc.runtime,
        exc.files,
        exc.struct,
        exc.resource,
        exc.traffic
    ]
    
    def __init__(self, obj):
        super(UpdateChute, self).__init__(obj)




###################################################################################################
## Module functions and variables
###################################################################################################
UPDATE_CLASSES = {
    "CHUTE": UpdateChute
}

def parse(obj):
    """
    Determines the update type and returns the proper class.
    """
    uclass = obj.get('updateClass', None)
    cls = UPDATE_CLASSES.get(uclass, None)

    if(cls is None):
        raise Exception('BadUpdateType')
    return cls(obj)