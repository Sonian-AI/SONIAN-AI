const { Keypair, Connection, clusterApiUrl, PublicKey } = require('@solana/web3.js');
const { Metaplex, keypairIdentity, bundlrStorage } = require('@metaplex-foundation/js');
const fs = require('fs');

// Твоят private key string от Phantom (вграден директно)
const secretKeyString = 'hPgk1zc18igJAFurUyFced83SRUorCTE4AXKMb4iW2eV23Lw93peLqJ65Z4wujgrDH6rYm42zy3pbHYRNZHaBvP';
const secretKeyBytes = Buffer.from(secretKeyString, 'base58');
const wallet = Keypair.fromSecretKey(secretKeyBytes);
console.log('Wallet loaded! Public Key:', wallet.publicKey.toString());

// Свържи се към devnet
const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');

// Metaplex setup
const metaplex = Metaplex.make(connection)
  .use(keypairIdentity(wallet))
  .use(bundlrStorage({ address: 'https://devnet.bundlr.network' }));

async function updateTokenMetadata() {
  try {
    // Замени с твоя mint address от Phantom (SONIAN токен > View on Explorer > копирай от URL-а)
    const mintAddress = new PublicKey('YOUR_MINT_ADDRESS_HERE'); // напр. 'F1s3abc123...'

    // Намери токена
    const token = await metaplex.nfts().findByMint({ mintAddress });

    // Чети metadata.json от папката
    const metadataRaw = fs.readFileSync('./metadata.json', 'utf8');
    let metadata = JSON.parse(metadataRaw);

    // Добави снимка (локална logo.jpg – Metaplex ще я качи автоматично)
    metadata.image = './logo.jpg';
    metadata.properties.files[0].uri = './logo.jpg';

    // Качи метаданни (description, снимка и т.н.)
    const { uri } = await metaplex.nfts().uploadMetadata(metadata);

    // Ъпдейтни токена
    await metaplex.nfts().update({
      nftOrSft: token,
      uri: uri,
    });

    console.log('Готово! Метаданните са обновени със снимка и description.');
    console.log('URI:', uri);
    console.log('Провери в Phantom (refresh) или https://explorer.solana.com/address/' + mintAddress.toString() + '?cluster=devnet');
  } catch (error) {
    console.error('Грешка:', error);
  }
}

updateTokenMetadata();