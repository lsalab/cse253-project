-- luacheck: read_globals Proto ProtoField base DissectorTable PI_MALFORMED PI_ERROR wtap
-- luacheck: allow_defined

nefics_proto = Proto("nefics", "NEFICS Simulation")

nefics_messageid = {
    [0x00000000] = 'MSG_WERE',
    [0x00000001] = 'MSG_ISAT',
    [0x00000002] = 'MSG_GETV',
    [0x00000003] = 'MSG_VOLT',
    [0x00000004] = 'MSG_GREQ',
    [0x00000005] = 'MSG_TREQ',
    [0xFFFFFFFE] = 'MSG_NRDY',
    [0xFFFFFFFF] = 'MSG_UKWN'
}

fields = nefics_proto.fields
fields.sender   = ProtoField.uint32("nefics.sender", "Sender ID", base.DEC)
fields.receiver = ProtoField.uint32("nefics.receiver", "Receiver ID", base.DEC)
fields.message  = ProtoField.uint32("nefics.message", "Message ID", base.DEC_HEX, nefics_messageid)
fields.intarg0  = ProtoField.uint32("nefics.int0", "Integer Argument 0", base.DEC_HEX)
fields.intarg1  = ProtoField.uint32("nefics.int1", "Integer Argument 1", base.DEC_HEX)
fields.fltarg0  = ProtoField.float("nefics.flt0", "Float Argument 0", base.DEC)
fields.fltarg1  = ProtoField.float("nefics.flt1", "Float Argument 1", base.DEC)

function nefics_proto.dissector(buffer, pinfo, tree)
    length = buffer:len()
    if length ~= 28 then return end

    pinfo.cols.protocol = nefics_proto.name

    local subtree = tree:add(nefics_proto, buffer(), "NEFICS Simulation Data")
    subtree:add_le(fields.sender, buffer(0, 4))
    subtree:add_le(fields.receiver, buffer(4, 4))
    subtree:add_le(fields.message, buffer(8, 4))
    subtree:add_le(fields.intarg0, buffer(12, 4))
    subtree:add_le(fields.intarg1, buffer(16, 4))
    subtree:add_le(fields.fltarg0, buffer(20, 4))
    subtree:add_le(fields.fltarg1, buffer(24, 4))
end

local udp_port = DissectorTable.get("udp.port")
udp_port:add(20202, nefics_proto)