const { Keypair, Connection, clusterApiUrl, PublicKey, SystemProgram, SYSVAR_RENT_PUBKEY, Transaction, sendAndConfirmTransaction } = require('@solana/web3.js');
const { TOKEN_PROGRAM_ID, getOrCreateAssociatedTokenAccount, mintTo, createInitializeMint2Instruction } = require('@solana/spl-token');
const bs58 = require('bs58');
const fs = require('fs');
const { findMetadataPda, createCreateMetadataAccountV3Instruction } = require('@metaplex-foundation/mpl-token-metadata');
const TOKEN_METADATA_PROGRAM_ID = new PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s');

// Твоя private key string от Phantom (вграден директно)
const secretKeyString = 'hPgk1zc18igJAFurUyFced83SRUorCTE4AXKMb4iW2eV23Lw93peLqJ65Z4wujgrDH6rYm42zy3pbHYRNZHaBvP';
const secretKeyBytes = bs58.decode(secretKeyString);
const wallet = Keypair.fromSecretKey(secretKeyBytes);
console.log('Wallet loaded! Public Key:', wallet.publicKey.toString());

// Свържи се към devnet
const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');

// Твоя mint address (вграден директно)
const mintAddress = new PublicKey('6q1GqCegiGUVQ9fbUNNPChBBJP5qMFRh36YA3Bh15xsS');

// Метаданни (вграден директно, с Pinata снимка и description)
const metadata = {
  name: 'SONIAN AI Rewards Token',
  symbol: 'SONIAN',
  uri: 'https://rose-important-mule-20.mypinata.cloud/ipfs/bafkreie5kgwlyjaj2f2yodm4ou4gw2a7hm4adhkc246zsljazzgivtpawe',
  sellerFeeBasisPoints: 0,
  creators: null,
  collection: null,
  uses: null,
};

async function createOrUpdateToken() {
  try {
    let mint = mintAddress;
    console.log('Using existing mint:', mint.toString());

    // Създай token account за wallet-а
    const tokenAccount = await getOrCreateAssociatedTokenAccount(
      connection,
      wallet,
      mint,
      wallet.publicKey
    );

    // Mint 1 милиард токени
    await mintTo(
      connection,
      wallet,
      mint,
      tokenAccount.address,
      wallet,
      1000000000
    );
    console.log('Minted 1 billion SONIAN tokens!');

    // Намери metadata PDA
    const [metadataPDA] = PublicKey.findProgramAddressSync(
      [
        Buffer.from('metadata'),
        TOKEN_METADATA_PROGRAM_ID.toBuffer(),
        mint.toBuffer(),
      ],
      TOKEN_METADATA_PROGRAM_ID
    );

    // Създай metadata instruction
    const createMetadataIx = createCreateMetadataAccountV3Instruction(
      {
        metadata: metadataPDA,
        mint: mint,
        mintAuthority: wallet.publicKey,
        payer: wallet.publicKey,
        updateAuthority: wallet.publicKey,
        systemProgram: SystemProgram.programId,
        rent: SYSVAR_RENT_PUBKEY,
      },
      {
        createMetadataAccountArgsV3: {
          data: {
            name: metadata.name,
            symbol: metadata.symbol,
            uri: metadata.uri,
            sellerFeeBasisPoints: metadata.sellerFeeBasisPoints,
            creators: metadata.creators,
            collection: metadata.collection,
            uses: metadata.uses,
          },
          isMutable: true,
          collectionDetails: null,
        },
      }
    );

    // Изпрати transaction
    const transaction = new Transaction().add(createMetadataIx);
    const signature = await sendAndConfirmTransaction(
      connection,
      transaction,
      [wallet]
    );

    console.log('Готово! Token updated with metadata.');
    console.log('Mint: ', mint.toString());
    console.log('Metadata PDA: ', metadataPDA.toString());
    console.log('Transaction Signature: ', signature);
    console.log('Провери в Phantom (refresh) или https://explorer.solana.com/address/' + mint.toString() + '?cluster=devnet');
  } catch (error) {
    console.error('Грешка:', error);
  }
}

createOrUpdateToken();