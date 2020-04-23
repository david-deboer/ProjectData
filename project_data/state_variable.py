"""General simple state variable module."""
from argparse import Namespace


class StateVar:
    """
    General state variable class.

    This can be used as a base class or namespace for state variables.  One may
    strictly enforce only using allowed variables or, if that is an empty list,
    allow any.

    The internal state variables for this class are under the self._sv Namespace.
    State methods start with sv_.  The only exception is 'state', which will likely
    get overwritten in a child class.
    """

    sv_internal_settable_states = ['label', 'verbose', 'description']

    def __init__(self, allowed_variables=[], label='State variables', verbose=True,
                 description='State variable class'):
        """
        Initialize state variable class.

        The parameters set the internal state.  If allowed_variables is a list, then
        that is "enforced".  Variables initialized via 'sv_initialize' get added to
        the allowed_variables list.

        Parameters
        ----------
        allowed_variables : list/str or None
            If list/str, will only allow these variables but will add initialized
            variables to it.  String gets converted by split(',')
        label : str
            Name of state variable set (header when shown)
        verbose : bool
            Internal verbose for printing list etc
        description : str
            Broader description if desired.
        """
        self._sv = Namespace(label=label, verbose=verbose, description=description)
        if isinstance(allowed_variables, str):
            allowed_variables = allowed_variables.split(',')
        self._sv.allowed_variables = allowed_variables
        self._sv.state_variables = {}

    def sv_set_internal(self, **kwargs):
        """Set the small set of internal states."""
        for k, v in kwargs.items():
            if k not in self.sv_internal_settable_states:
                print("{} not allowed internal state option".format(k))
                continue
            setattr(self._sv, k, v)

    def sv_list_internal(self):
        """List the set of internal states as well as state_variables."""
        print("Internal set states:  ")
        for x in self.sv_internal_settable_states:
            print("\t{:12s}   {}".format(x, getattr(self._sv, x)))
        if not isinstance(self._sv.allowed_variables, list):
            print("Allowed variables:  ", self._sv.allowed_variables)
        else:
            print("No restricted variables")
        print("State variables:")
        for k, v in self._sv.state_variables.items():
            print("\t{:20s}   {}".format(k, v))

    def sv_initialize(self, variable, value, description=None, var_type='auto'):
        """
        Initialize the state_variables.

        Optionally, one may initialize a state variable, which includes it in
        self.allowed_variables, if it is not None.  It also allows one to
        include a description and var_type.

        Parameters
        ----------
        variable : str
            Variable name
        value : *
            Initial value assigned.  Type is set to type(value)
        description : str or None
            Description for that variable
        var_type : None or 'auto'
            Enforce type or not
        """
        if isinstance(self._sv.allowed_variables, list):
            self._sv.allowed_variables.append(variable)
        if var_type == 'auto':
            var_type = type(value)
        else:
            var_type = None
        self._sv.state_variables[variable] = {'description': description,
                                              'var_type': var_type}
        this_init = {variable: value}
        self.sv_state(**this_init)

    def sv_load(self, load_from, keys_to_use=None, use_to_init=False, var_type='auto'):
        """
        Load the state_variables from a dictionary or file.

        If keys_to_use is set, it will only use dicts under those keys (in case the state
        variables are part of a bigger e.g. json file.)

        Parameters
        ----------
        load_from : str or dict
            If str, it will read from a json file of that name.
            If dict, it will use that dictionary.
        keys_to_use : list, csv-list str, or None
            If not None, it will only use dicts under the specified keys.
        use_to_init : bool or str
            If True (or str), it will run initialize with the variables.
                If str, it will use that as the description.
        var_type : 'auto' or None
            If 'auto', it will enforce using the type of the variable.
        """
        if isinstance(keys_to_use, str):
            keys_to_use = keys_to_use.split(',')
        if isinstance(load_from, str):
            import json
            with open(load_from, 'r') as f:
                load_from = json.load(f)
        if not isinstance(load_from, dict):
            print("{} not supported.".format(type(load_from)))
        if keys_to_use is None:
            state_dict = load_from
        else:
            state_dict = {}
            for key in keys_to_use:
                for k, v in load_from[key].items():
                    state_dict[k] = v
        if use_to_init:
            if isinstance(use_to_init, str):
                desc = use_to_init
            else:
                desc = self._sv.label
            for k, v in state_dict.items():
                self.sv_initialize(k, v, description=desc, var_type=var_type)
        else:
            self.sv_state(**state_dict)

    def state(self, sv_show=False, **kwargs):
        """
        Show or set the state_variables.

        This is the internal version - likely to get over-written by a child class.
        """
        self.sv_state(sv_show, **kwargs)

    def sv_state(self, sv_show=False, **kwargs):
        """Functional internal version to set states."""
        if sv_show or (not len(kwargs.keys()) and self._sv.verbose):
            print('<{}>'.format(self._sv.label))
            for sv in sorted(list(self._sv.state_variables.keys())):
                print('\t{}:  {}'.format(sv, getattr(self, sv)))
            return

        for k, v in kwargs.items():
            if not isinstance(self._sv.allowed_variables, list):
                update_it = True
            else:
                update_it = k in self._sv.allowed_variables
            if update_it:
                if k not in self._sv.state_variables.keys():
                    self._sv.state_variables[k] = {'description': 'None', 'var_type': None}
                if self._sv.state_variables[k]['var_type'] is not None:
                    if self._sv.state_variables[k]['var_type'] == list and isinstance(v, str):
                        v = v.split(',')
                    if type(v) != self._sv.state_variables[k]['var_type']:
                        print("Wrong type for {}".format(k))
                        continue
                setattr(self, k, v)
            else:
                if self._sv.verbose:
                    print("Updating {} is not allowed".format(k))
