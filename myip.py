import struct
from myiputils import *

tabela_encaminhamento = []


class CamadaRede:
    def __init__(self, enlace):
        """
        Inicia a camada de rede. Recebe como argumento uma implementação
        de camada de enlace capaz de localizar os next_hop (por exemplo,
        Ethernet com ARP).
        """
        self.callback = None
        self.enlace = enlace
        self.enlace.registrar_recebedor(self.__raw_recv)
        self.meu_endereco = None

    def __raw_recv(self, datagrama):
        dscp, ecn, identification, flags, frag_offset, ttl, proto, \
           src_addr, dst_addr, payload = read_ipv4_header(datagrama)
        if dst_addr == self.meu_endereco:
            # atua como host
            if proto == IPPROTO_TCP and self.callback:
                self.callback(src_addr, dst_addr, payload)
        else:
            # atua como roteador
            next_hop = self._next_hop(dst_addr)
            # TODO: Trate corretamente o campo TTL do datagrama
            ttl -= 1
            if ttl > 0:
                # reconstruir o datagrama com o novo TTL e enviar
                novo_datagrama = make_ipv4_header(payload, src_addr, dst_addr, ttl) + payload
                self.enlace.enviar(novo_datagrama, next_hop)

    def _next_hop(self, dest_addr):
        # TODO: Use a tabela de encaminhamento para determinar o próximo salto
        # (next_hop) a partir do endereço de destino do datagrama (dest_addr).
        # Retorne o next_hop para o dest_addr fornecido.
        global tabela_encaminhamento
        dest_addr_binario = "".join([bin(int(x) + 256)[3:] for x in dest_addr.split('.')])

        possiveis_cidrs = []
        for linha in tabela_encaminhamento:
            cidr_decimal, prefix = linha[0].split('/')
            cidr_binario = "".join([bin(int(x) + 256)[3:] for x in cidr_decimal.split('.')])
            prefix = int(prefix)
            if cidr_binario[:prefix] == dest_addr_binario[:prefix]:
                possiveis_cidrs.append({'binario': cidr_binario, 'hop': linha[1]})

        if len(possiveis_cidrs) == 0:
            return None

        if len(possiveis_cidrs) == 1:
            return possiveis_cidrs[0]['hop']

        if len(possiveis_cidrs) > 1:
            for p in possiveis_cidrs:
                qtd_match = 0
                for i in range(32):
                    if p['binario'][i] == dest_addr_binario[i]:
                        qtd_match += 1
                    else:
                        break
                p['qtd_match'] = qtd_match
            maior = possiveis_cidrs[0]
            for p in possiveis_cidrs:
                if p['qtd_match'] > maior['qtd_match']:
                    maior = p
            return maior['hop']

    def definir_endereco_host(self, meu_endereco):
        """
        Define qual o endereço IPv4 (string no formato x.y.z.w) deste host.
        Se recebermos datagramas destinados a outros endereços em vez desse,
        atuaremos como roteador em vez de atuar como host.
        """
        self.meu_endereco = meu_endereco

    def definir_tabela_encaminhamento(self, tabela):
        """
        Define a tabela de encaminhamento no formato
        [(cidr0, next_hop0), (cidr1, next_hop1), ...]

        Onde os CIDR são fornecidos no formato 'x.y.z.w/n', e os
        next_hop são fornecidos no formato 'x.y.z.w'.
        """
        # TODO: Guarde a tabela de encaminhamento. Se julgar conveniente,
        # converta-a em uma estrutura de dados mais eficiente.
        global tabela_encaminhamento
        tabela_encaminhamento = []
        for linha in tabela:
            cidr = linha[0]
            next_hop = linha[1]
            tabela_encaminhamento.append((cidr, next_hop))
        pass

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de rede
        """
        self.callback = callback

    def enviar(self, segmento, dest_addr):
        """
        Envia segmento para dest_addr, onde dest_addr é um endereço IPv4
        (string no formato x.y.z.w).
        """
        next_hop = self._next_hop(dest_addr)
        # TODO: Assumindo que a camada superior é o protocolo TCP, monte o
        # datagrama com o cabeçalho IP, contendo como payload o segmento.
        datagrama = make_ipv4_header(segmento, self.meu_endereco, dest_addr) + segmento
        self.enlace.enviar(datagrama, next_hop)


def make_ipv4_header(segmento, src_addr, dest_addr, ttl=64):
    version = 4 << 4
    ihl = 5
    vihl = version | ihl
    dscp = 0 << 6
    ecn = 0
    dscpecn = dscp | ecn
    total_len = len(segmento) + 20
    identification = 0
    flagsfrag = 0
    ttl = ttl
    proto = 6
    s = int.from_bytes(str2addr(src_addr), "big")
    d = int.from_bytes(str2addr(dest_addr), "big")
    header = struct.pack('!BBHHHBBHII', vihl, dscpecn, total_len,
        identification, flagsfrag, ttl, proto, 0, s, d)
    checksum = calc_checksum(header)
    novo_header = struct.pack('!BBHHHBBHII', vihl, dscpecn, total_len, identification,
                    flagsfrag, ttl, proto, checksum, s, d)
    return novo_header
