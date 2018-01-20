from __future__ import absolute_import, print_function


class Records_fields:
    def __init__(self):
        self.required = ['refname', 'value', 'description', 'dtype', 'status', 'owner', 'other', 'notes', 'id', 'commentary']
        self.find_allowed = ['dtype', 'status', 'owner', 'other', 'id']
        self.pass_thru = ['any', 'all', 'n/a', -1]  # do all if one of these

    def set_find_default(self):
        self.dtype = ['all']
        self.owner = ['all']
        self.other = ['all']
        self.status = ['all']
        self.id = [-1]

    def find_check(self, Finding, rec, status):
        owner = (rec['owner'] if rec['owner'] is not None else [])
        if isinstance(owner, str):
            owner = [owner]
        owner = [x.lower() for x in owner]
        owner_ok = False
        for i_owner in Finding.owner:
            owner_ok = (i_owner.lower() in self.pass_thru) or (i_owner.lower() in owner)
            if owner_ok:
                break
        dtype = str(rec['dtype']).lower()
        dtype_ok = False
        for i_dtype in Finding.dtype:
            if (i_dtype.lower() in self.pass_thru) or (i_dtype.lower() == dtype):
                dtype_ok = True
                break
        other = str(rec['other']).lower()
        other_ok = False
        for i_other in Finding.other:
            if (i_other.lower() in self.pass_thru) or (i_other.lower() == other):
                other_ok = True
                break
        status = status[0].lower()
        status_ok = False
        for i_status in Finding.status:
            if (i_status.lower() in self.pass_thru) or (i_status.lower() == status):
                status_ok = True
                break
        rid = rec['id']
        id_ok = False
        for i_id in Finding.id:
            if i_id in self.pass_thru or i_id == rid:
                id_ok = True
                break
        return owner_ok and dtype_ok and other_ok and status_ok and id_ok
